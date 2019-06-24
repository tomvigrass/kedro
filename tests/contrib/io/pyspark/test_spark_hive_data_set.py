# Copyright 2018-2019 QuantumBlack Visual Analytics Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND
# NONINFRINGEMENT. IN NO EVENT WILL THE LICENSOR OR OTHER CONTRIBUTORS
# BE LIABLE FOR ANY CLAIM, DAMAGES, OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF, OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
# The QuantumBlack Visual Analytics Limited (“QuantumBlack”) name and logo
# (either separately or in combination, “QuantumBlack Trademarks”) are
# trademarks of QuantumBlack. The License does not grant you any right or
# license to the QuantumBlack Trademarks. You may not use the QuantumBlack
# Trademarks or any confusingly similar mark as a trademark for your product,
#     or use the QuantumBlack Trademarks in any other manner that might cause
# confusion in the marketplace, including but not limited to in advertising,
# on websites, or on software.
#
# See the License for the specific language governing permissions and
# limitations under the License.
import os
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.types import IntegerType, StringType, StructField, StructType

from kedro.contrib.io.pyspark.spark_hive_data_set import SparkHiveDataSet

TESTSPARKDIR = "test_spark_dir"


@pytest.fixture(scope="module", autouse=True)
def spark_hive_session(spark_session_base):
    with TemporaryDirectory(TESTSPARKDIR) as tmpdir:
        os.chdir(tmpdir)
        spark = (
            SparkSession.builder.config(
                "spark.local.dir", (Path(tmpdir) / "spark_local").absolute()
            )
            .config("spark.sql.warehouse.dir", (Path(tmpdir) / "warehouse").absolute())
            .enableHiveSupport()
            .getOrCreate()
        )
        spark.sql("create database default_1")
        spark.sql("create database default_2")
        _write_hive(spark, _generate_spark_df_one(), "default_1", "table_1")
        yield spark
        spark.stop()


def assert_df_equal(expected, result):
    def indexRDD(data_frame):
        return data_frame.rdd.zipWithIndex().map(lambda x: (x[1], x[0]))

    index_expected = indexRDD(expected)
    index_result = indexRDD(result)
    assert (
        index_expected.cogroup(index_result)
        .map(lambda x: tuple(map(list, x[1])))
        .filter(lambda x: x[0] != x[1])
        .take(1)
        == []
    )


def _write_hive(spark_session: SparkSession, dataset: DataFrame, database, table):
    dataset.createOrReplaceTempView("tmp")
    spark_session.sql("use " + database)
    spark_session.sql("create table {table} as select * from tmp".format(table=table))


def _generate_spark_df_one():
    schema = StructType(
        [
            StructField("name", StringType(), True),
            StructField("age", IntegerType(), True),
        ]
    )
    data = [("Alex", 31), ("Bob", 12), ("Clarke", 65), ("Dave", 29)]
    return SparkSession.builder.getOrCreate().createDataFrame(data, schema).coalesce(1)


def _generate_spark_df_upsert():
    schema = StructType(
        [
            StructField("name", StringType(), True),
            StructField("age", IntegerType(), True),
        ]
    )
    data = [("Alex", 99), ("Jeremy", 55)]
    return SparkSession.builder.getOrCreate().createDataFrame(data, schema).coalesce(1)


def _generate_spark_df_upsert_expected():
    schema = StructType(
        [
            StructField("name", StringType(), True),
            StructField("age", IntegerType(), True),
        ]
    )
    data = [("Alex", 99), ("Bob", 12), ("Clarke", 65), ("Dave", 29), ("Jeremy", 55)]
    return SparkSession.builder.getOrCreate().createDataFrame(data, schema).coalesce(1)


def test_cant_pickle():
    import pickle

    with pytest.raises(pickle.PicklingError):
        pickle.dumps(
            SparkHiveDataSet(
                database="default_1", table="table_1", write_mode="overwrite"
            )
        )


def test_read_existing_table():
    dataset = SparkHiveDataSet(
        database="default_1", table="table_1", write_mode="overwrite"
    )
    assert_df_equal(_generate_spark_df_one(), dataset.load())


def test_overwrite_empty_table(spark_hive_session):
    spark_hive_session.sql(
        "create table default_1.test_overwrite_empty_table (name string, age integer)"
    ).take(1)
    dataset = SparkHiveDataSet(
        database="default_1", table="test_overwrite_empty_table", write_mode="overwrite"
    )
    dataset.save(_generate_spark_df_one())
    assert_df_equal(dataset.load(), _generate_spark_df_one())


def test_fail_data_correctness(spark_hive_session):
    spark_hive_session.sql(
        "create table default_1.test_fail_data_correctness (name string, age integer)"
    ).take(1)
    dataset = SparkHiveDataSet(
        database="default_1", table="test_fail_data_correctness", write_mode="overwrite"
    )
    dataset.save(_generate_spark_df_one().union(_generate_spark_df_one()))
    with pytest.raises(AssertionError):
        assert_df_equal(dataset.load(), _generate_spark_df_one())


def test_overwrite_not_empty_table(spark_hive_session):
    spark_hive_session.sql(
        "create table default_1.test_overwrite_full_table (name string, age integer)"
    ).take(1)
    dataset = SparkHiveDataSet(
        database="default_1", table="test_overwrite_full_table", write_mode="overwrite"
    )
    dataset.save(_generate_spark_df_one())
    dataset.save(_generate_spark_df_one())
    assert_df_equal(dataset.load(), _generate_spark_df_one())


def test_insert_not_empty_table(spark_hive_session):
    spark_hive_session.sql(
        "create table default_1.test_insert_not_empty_table (name string, age integer)"
    ).take(1)
    dataset = SparkHiveDataSet(
        database="default_1", table="test_insert_not_empty_table", write_mode="insert"
    )
    dataset.save(_generate_spark_df_one())
    dataset.save(_generate_spark_df_one())
    assert_df_equal(
        dataset.load(), _generate_spark_df_one().union(_generate_spark_df_one())
    )


def test_upsert_config_err():
    # no pk provided should prompt config error
    with pytest.raises(
        ValueError, match="table_pk must be set to utilise upsert read mode"
    ):
        SparkHiveDataSet(database="default_1", table="table_1", write_mode="upsert")


def test_upsert_empty_table(spark_hive_session):
    spark_hive_session.sql(
        "create table default_1.test_upsert_empty_table (name string, age integer)"
    ).take(1)
    dataset = SparkHiveDataSet(
        database="default_1",
        table="test_upsert_empty_table",
        write_mode="upsert",
        table_pk=["name"],
    )
    dataset.save(_generate_spark_df_one())
    assert_df_equal(dataset.load().sort("name"), _generate_spark_df_one().sort("name"))


def test_upsert_not_empty_table(spark_hive_session):
    spark_hive_session.sql(
        "create table default_1.test_upsert_not_empty_table (name string, age integer)"
    ).take(1)
    dataset = SparkHiveDataSet(
        database="default_1",
        table="test_upsert_not_empty_table",
        write_mode="upsert",
        table_pk=["name"],
    )
    dataset.save(_generate_spark_df_one())
    dataset.save(_generate_spark_df_upsert())

    assert_df_equal(dataset.load().sort("name"), _generate_spark_df_upsert_expected().sort("name"))
