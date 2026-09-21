from pathlib import Path

from patchdiff.input.base import BaseReader
from patchdiff.input.csv import CSVReader
from patchdiff.input.excel import ExcelReader

_readers = {
    ".csv": CSVReader,
    ".xlsx": ExcelReader,
    ".xls": ExcelReader,
}

class BaseReaderFactory:

    @staticmethod
    def create_reader( path: str) -> BaseReader:
        extension = Path(path).suffix.lower()

        try:
            reader_class = _readers[extension]
        except KeyError:
            raise ValueError(
                f"Unsupported file type: {extension}"
            )

        return reader_class()