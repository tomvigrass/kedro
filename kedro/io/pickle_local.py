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
# The QuantumBlack Visual Analytics Limited ("QuantumBlack") name and logo
# (either separately or in combination, "QuantumBlack Trademarks") are
# trademarks of QuantumBlack. The License does not grant you any right or
# license to the QuantumBlack Trademarks. You may not use the QuantumBlack
# Trademarks or any confusingly similar mark as a trademark for your product,
#     or use the QuantumBlack Trademarks in any other manner that might cause
# confusion in the marketplace, including but not limited to in advertising,
# on websites, or on software.
#
# See the License for the specific language governing permissions and
# limitations under the License.

"""``PickleLocalDataSet`` loads and saves a Python object to a
local pickle file. The underlying functionality is
supported by the ``pickle`` and ``joblib`` libraries, so it supports
all allowed options for loading and saving pickle files.
"""

import pickle
from pathlib import Path
from typing import Any, Dict

from kedro.io.core import AbstractVersionedDataSet, DataSetError, Version

try:
    import joblib
except ImportError:
    joblib = None


class PickleLocalDataSet(AbstractVersionedDataSet):
    """``PickleLocalDataSet`` loads and saves a Python object to a
    local pickle file. The underlying functionality is
    supported by the pickle and joblib libraries, so it supports
    all allowed options for loading and saving pickle files.

    Example:
    ::

        >>> from kedro.io import PickleLocalDataSet
        >>> import pandas as pd
        >>>
        >>> dummy_data =  pd.DataFrame({'col1': [1, 2],
        >>>                             'col2': [4, 5],
        >>>                             'col3': [5, 6]})
        >>> data_set = PickleLocalDataSet(filepath="data.pkl",
        >>>                               backend='pickle',
        >>>                               load_args=None,
        >>>                               save_args=None)
        >>> data_set.save(dummy_data)
        >>> reloaded = data_set.load()
    """

    BACKENDS = {"pickle": pickle, "joblib": joblib}

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        filepath: str,
        backend: str = "pickle",
        load_args: Dict[str, Any] = None,
        save_args: Dict[str, Any] = None,
        version: Version = None,
    ) -> None:
        """Creates a new instance of ``PickleLocalDataSet`` pointing to a
        concrete filepath. ``PickleLocalDataSet`` can use two backends to
        serialise objects to disk:

        pickle.dump: https://docs.python.org/3/library/pickle.html#pickle.dump

        joblib.dump: https://pythonhosted.org/joblib/generated/joblib.dump.html

        and it can use two backends to load serialised objects into memory:

        pickle.load: https://docs.python.org/3/library/pickle.html#pickle.load

        joblib.load: https://pythonhosted.org/joblib/generated/joblib.load.html

        Joblib tends to exhibit better performance in case objects store NumPy
        arrays:
        http://gael-varoquaux.info/programming/new_low-overhead_persistence_in_joblib_for_big_data.html.

        Args:
            filepath: path to a pkl file.
            backend: backend to use, must be one of ['pickle', 'joblib'].
            load_args: Options for loading pickle files. Refer to the help
                file of ``pickle.load`` or ``joblib.load`` for options.
            save_args: Options for saving pickle files. Refer to the help
                file of ``pickle.dump`` or ``joblib.dump`` for options.
            version: If specified, should be an instance of
                ``kedro.io.core.Version``. If its ``load`` attribute is
                None, the latest version will be loaded. If its ``save``
                attribute is None, save version will be autogenerated.

        Raises:
            ValueError: If 'backend' is not one of ['pickle', 'joblib'].
            ImportError: If 'backend' could not be imported.

        """
        super().__init__(Path(filepath), version)
        default_save_args = {}  # type: Dict[str, Any]
        default_load_args = {}  # type: Dict[str, Any]

        if backend not in ["pickle", "joblib"]:
            raise ValueError(
                "backend should be one of ['pickle', 'joblib'], got %s" % backend
            )
        if backend == "joblib" and joblib is None:
            raise ImportError(
                "selected backend 'joblib' could not be "
                "imported. Make sure it is installed."
            )

        self._backend = backend
        self._load_args = (
            {**default_load_args, **load_args}
            if load_args is not None
            else default_load_args
        )
        self._save_args = (
            {**default_save_args, **save_args}
            if save_args is not None
            else default_save_args
        )

    def _load(self) -> Any:
        load_path = Path(self._get_load_path())
        with load_path.open("rb") as local_file:
            result = self.BACKENDS[self._backend].load(local_file, **self._load_args)
        return result

    def _save(self, data: Any) -> None:
        save_path = Path(self._get_save_path())
        save_path.parent.mkdir(parents=True, exist_ok=True)

        with save_path.open("wb") as local_file:
            self.BACKENDS[self._backend].dump(data, local_file, **self._save_args)

        load_path = Path(self._get_load_path())
        self._check_paths_consistency(load_path.absolute(), save_path.absolute())

    def _describe(self) -> Dict[str, Any]:
        return dict(
            filepath=self._filepath,
            backend=self._backend,
            load_args=self._load_args,
            save_args=self._save_args,
            version=self._version,
        )

    def _exists(self) -> bool:
        try:
            path = self._get_load_path()
        except DataSetError:
            return False
        return Path(path).is_file()
