import pytest

from patchdiff.input.csv import CSVReader
from patchdiff.input.excel import ExcelReader
from patchdiff.input.factory import BaseReaderFactory


@pytest.mark.parametrize(
    "path,expected_type",
    [
        ("patch.csv", CSVReader),
        ("patch.CSV", CSVReader),
        ("patch.xlsx", ExcelReader),
        ("patch.xls", ExcelReader),
        ("folder/nested/patch.csv", CSVReader),
    ],
)
def test_creates_expected_reader_for_extension(path, expected_type):
    reader = BaseReaderFactory.create_reader(path)

    assert isinstance(reader, expected_type)


def test_unsupported_extension_raises_value_error():
    with pytest.raises(ValueError, match="Unsupported file type"):
        BaseReaderFactory.create_reader("patch.txt")


def test_missing_extension_raises_value_error():
    with pytest.raises(ValueError, match="Unsupported file type"):
        BaseReaderFactory.create_reader("patch")
