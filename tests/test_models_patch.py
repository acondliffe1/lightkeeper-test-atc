from datetime import date

import pytest

from patchdiff.models.patch import Patch
from patchdiff.models.row import END_OF_TIME, PatchRow


def _row(**extra):
    return PatchRow.model_validate(extra)


def test_from_patch_row_uses_first_extra_column_as_key():
    row = _row(Issuer="JBL", Country="USA", Sector="Computers")

    patch = Patch.from_patch_row(row)

    assert patch.key_value == "JBL"


def test_from_patch_row_excludes_key_field_from_values():
    row = _row(Issuer="JBL", Country="USA", Sector="Computers")

    patch = Patch.from_patch_row(row)

    assert "Issuer" not in patch.values
    assert patch.values == {"Country": "USA", "Sector": "Computers"}


def test_from_patch_row_drops_none_values():
    row = _row(Issuer="JBL", Country="USA", Conviction=None)

    patch = Patch.from_patch_row(row)

    assert "Conviction" not in patch.values


def test_from_patch_row_carries_dates_through():
    row = _row(BeginDate="20240201", Issuer="FR", Conviction="Low")

    patch = Patch.from_patch_row(row)

    assert patch.begin_date == date(2024, 2, 1)
    assert patch.end_date == END_OF_TIME


def test_from_patch_row_raises_without_extra_columns():
    # A PatchRow with no extra data can't actually be constructed (it fails
    # its own validation), but from_patch_row should still guard the
    # invariant defensively.
    row = PatchRow.model_construct(
        begin_date=date(1900, 1, 1), end_date=END_OF_TIME
    )

    with pytest.raises(ValueError, match="key field"):
        Patch.from_patch_row(row)


@pytest.mark.parametrize(
    "begin_date,end_date,expected",
    [
        (date(2024, 1, 1), date(2024, 12, 31), True),
        (date(2023, 1, 1), date(2023, 12, 31), False),
        (date(2024, 6, 1), date(2024, 6, 1), True),
    ],
)
def test_in_period_overlap(begin_date, end_date, expected):
    patch = Patch(
        begin_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
        key_value="FR",
        values={},
    )

    assert patch.in_period(begin_date, end_date) is expected
