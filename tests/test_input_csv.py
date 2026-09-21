from datetime import date
from math import isnan

from patchdiff.input.csv import CSVReader
from patchdiff.models.row import BEGINNING_OF_TIME, END_OF_TIME


def test_reads_all_rows(tmp_path):
    csv_path = tmp_path / "patch.csv"
    csv_path.write_text(
        "BeginDate,EndDate,Issuer,Country\n"
        ",,JBL,USA\n"
        ",,PIPR,FRA\n"
    )

    rows = CSVReader().read(str(csv_path))

    assert len(rows) == 2
    assert [row.model_extra["Issuer"] for row in rows] == ["JBL", "PIPR"]


def test_blank_dates_from_csv_default_to_open_range(tmp_path):
    csv_path = tmp_path / "patch.csv"
    csv_path.write_text("BeginDate,EndDate,Issuer\n,,JBL\n")

    row = CSVReader().read(str(csv_path))[0]

    assert row.begin_date == BEGINNING_OF_TIME
    assert row.end_date == END_OF_TIME


def test_dated_row_from_csv_is_parsed(tmp_path):
    csv_path = tmp_path / "patch.csv"
    csv_path.write_text("BeginDate,EndDate,Issuer\n20240201,,FR\n")

    row = CSVReader().read(str(csv_path))[0]

    assert row.begin_date == date(2024, 2, 1)
    assert row.end_date == END_OF_TIME


def test_missing_optional_column_value_is_nan(tmp_path):
    csv_path = tmp_path / "patch.csv"
    csv_path.write_text(
        "BeginDate,EndDate,Issuer,Conviction\n,,JBL,\n,,FR,Low\n"
    )

    rows = CSVReader().read(str(csv_path))

    jbl_conviction = rows[0].model_extra["Conviction"]
    assert isinstance(jbl_conviction, float) and isnan(jbl_conviction)
    assert rows[1].model_extra["Conviction"] == "Low"
