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

"""BioSequenceLocalDataSet loads and saves data to/from bio-sequence objects to
file.
"""
from os.path import isfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from Bio import SeqIO

from kedro.contrib.io import DefaultArgumentsMixIn
from kedro.io import AbstractDataSet


class BioSequenceLocalDataSet(DefaultArgumentsMixIn, AbstractDataSet):
    """``BioSequenceLocalDataSet`` loads and saves data to a sequence file.

    Example:
    ::

        >>> raw_sequence_list = [
        >>>     '>gi|2765658|emb|Z78533.1|CIZ78533'
        >>>     'C.irapeanum 5.8S rRNA gene and ITS1 and ITS2 DNA'
        >>>     'CGTAACAAGGTTTCCGTAGGTGAACCTGCGGAAGGATCATTGATGAGACCGTGGAATAAA'
        >>>     'CGATCGAGTGAATCCGGAGGACCGGTGTACTCAGCTCACCGGGGGCATTGCTCCCGTGGT'
        >>>     'GACCCTGATTTGTTGTTGGGCCGCCTCGGGAGCGTCCATGGCGGGTTTGAACCTCTAGCC'
        >>>     'CGGCGCAGTTTGGGCGCCAAGCCATATGAAAGCATCACCGGCGAATGGCATTGTCTTCCC'
        >>>     'CAAAACCCGGAGCGGCGGCGTGCTGTCGCGTGCCCAATGAATTTTGATGACTCTCGCAAA'
        >>>     'CGGGAATCTTGGCTCTTTGCATCGGATGGAAGGACGCAGCGAAATGCGATAAGTGGTGTG'
        >>>     'AATTGCAAGATCCCGTGAACCATCGAGTCTTTTGAACGCAAGTTGCGCCCGAGGCCATCA'
        >>>     'GGCTAAGGGCACGCCTGCTTGGGCGTCGCGCTTCGTCTCTCTCCTGCCAATGCTTGCCCG'
        >>>     'GCATACAGCCAGGCCGGCGTGGTGCGGATGTGAAAGATTGGCCCCTTGTGCCTAGGTGCG'
        >>>     'GCGGGTCCAAGAGCTGGTGTTTTGATGGCCCGGAACCCGGCAAGAGGTGGACGGATGCTG'
        >>>     'GCAGCAGCTGCCGTGCGAATCCCCCATGTTGTCGTGCTTGTCGGACAGGCAGGAGAACCC'
        >>>     'TTCCGAACCCCAATGGAGGGCGGTTGACCGCCATTCGGATGTGACCCCAGGTCAGGCGGG'
        >>>     'GGCACCCGCTGAGTTTACGC']
        >>> data_set = BioSequenceLocalDataSet(filepath="ls_orchid.fasta",
        >>>                                    load_args={"format": "fasta"},
        >>>                                    save_args={"format": "fasta"})
        >>> data_set.save(raw_sequence_list)
        >>> sequence_list = data_set.load()
        >>> assert raw_sequence_list.equals(sequence_list)

    """

    def _describe(self) -> Dict[str, Any]:
        return dict(
            filepath=self._filepath,
            load_args=self._load_args,
            save_args=self._save_args,
        )

    def __init__(
        self,
        filepath: str,
        load_args: Optional[Dict[str, Any]] = None,
        save_args: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Creates a new instance of ``BioSequenceLocalDataSet`` pointing
        to a concrete filepath.

        Args:
            filepath: path to sequence file
            load_args: Options for loading sequence files. Here you can find
                all supported file formats: https://biopython.org/wiki/SeqIO
            save_args: args supported by Biopython are 'handle' and 'format'.
                Handle by default is equal to ``filepath``.

        """
        self._filepath = filepath
        super().__init__(load_args, save_args)

    def _load(self) -> List:
        return list(SeqIO.parse(self._filepath, **self._load_args))

    def _save(self, data: list) -> None:
        save_path = Path(self._filepath)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        SeqIO.write(data, handle=str(save_path), **self._save_args)

    def _exists(self) -> bool:
        return isfile(self._filepath)
