import pytest

from patchdiff.input.excel import ExcelReader


def test_excel_reader_is_not_yet_implemented():
    # Pins current behavior: `raise ("Not yet Implemented")` raises
    # TypeError (a bare string isn't a valid exception), not
    # NotImplementedError. See README "Known limitations".
    with pytest.raises(TypeError):
        ExcelReader().read("patch.xlsx")
