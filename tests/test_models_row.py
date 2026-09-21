from datetime import date

import pytest
from pydantic import ValidationError

from patchdiff.models.row import BEGINNING_OF_TIME, END_OF_TIME, PatchRow


def test_defaults_open_dates_when_omitted():
    row = PatchRow.model_validate({"Issuer": "JBL"})

    assert row.begin_date == BEGINNING_OF_TIME
    assert row.end_date == END_OF_TIME


@pytest.mark.parametrize("blank", [None, "", "   ", float("nan")])
def test_blank_begin_date_defaults_to_beginning_of_time(blank):
    row = PatchRow.model_validate({"BeginDate": blank, "Issuer": "JBL"})

    assert row.begin_date == BEGINNING_OF_TIME


@pytest.mark.parametrize("blank", [None, "", "   ", float("nan")])
def test_blank_end_date_defaults_to_end_of_time(blank):
    row = PatchRow.model_validate({"EndDate": blank, "Issuer": "JBL"})

    assert row.end_date == END_OF_TIME


def test_parses_yyyymmdd_string():
    row = PatchRow.model_validate({"BeginDate": "20240201", "Issuer": "FR"})

    assert row.begin_date == date(2024, 2, 1)


def test_parses_yyyymmdd_numeric():
    # pandas reads a CSV column of dates like 20240201 as an int/float,
    # not a string, when the column is otherwise numeric.
    row = PatchRow.model_validate({"BeginDate": 20240201, "Issuer": "FR"})

    assert row.begin_date == date(2024, 2, 1)

    row = PatchRow.model_validate({"BeginDate": 20240201.0, "Issuer": "FR"})

    assert row.begin_date == date(2024, 2, 1)


def test_accepts_field_name_or_alias():
    by_alias = PatchRow.model_validate({"BeginDate": "20240201", "Issuer": "FR"})
    by_name = PatchRow.model_validate({"begin_date": "20240201", "Issuer": "FR"})

    assert by_alias.begin_date == by_name.begin_date == date(2024, 2, 1)


def test_extra_columns_are_preserved():
    row = PatchRow.model_validate(
        {"Issuer": "JBL", "Country": "USA", "Sector": "Computers"}
    )

    assert row.model_extra == {
        "Issuer": "JBL",
        "Country": "USA",
        "Sector": "Computers",
    }


def test_rejects_begin_date_after_end_date():
    with pytest.raises(ValidationError, match="begin_date must be before or equal"):
        PatchRow.model_validate(
            {"BeginDate": "20240301", "EndDate": "20240201", "Issuer": "FR"}
        )


def test_rejects_row_without_any_extra_column():
    with pytest.raises(ValidationError, match="at least one column"):
        PatchRow.model_validate({"BeginDate": "20240201"})
