from datetime import date, timedelta
from itertools import pairwise
from math import nan

from patchdiff.engine.engine import Engine
from patchdiff.input.csv import CSVReader
from patchdiff.models.patch import Patch
from patchdiff.models.row import END_OF_TIME

BOT = date(1900, 1, 1)
EOT = END_OF_TIME


def make_patch(key, values, begin=BOT, end=EOT):
    return Patch(begin_date=begin, end_date=end, key_value=key, values=values)


def test_single_open_ended_patch_resolves_to_one_period():
    patches = [make_patch("JBL", {"Country": "USA"})]

    outcome = Engine().resolve(patches)

    resolved = outcome.patch_groups["JBL"]
    assert len(resolved) == 1
    assert resolved[0].begin_date == BOT
    assert resolved[0].end_date == EOT
    assert resolved[0].values == {"Country": "USA"}


def test_later_dated_patch_splits_history_and_only_applies_going_forward():
    patches = [
        make_patch("FR", {"Country": "USA"}),
        make_patch(
            "FR",
            {"Country": "FRA", "Conviction": "Low"},
            begin=date(2024, 2, 1),
        ),
    ]

    resolved = Engine().resolve(patches).patch_groups["FR"]

    assert len(resolved) == 2

    before, after = resolved
    assert (before.begin_date, before.end_date) == (BOT, date(2024, 1, 31))
    assert before.values == {"Country": "USA"}

    assert (after.begin_date, after.end_date) == (date(2024, 2, 1), EOT)
    assert after.values == {"Country": "FRA", "Conviction": "Low"}


def test_later_patch_fields_merge_with_not_override_earlier_fields():
    # A later, narrower patch should only overwrite the fields it sets and
    # leave fields set by an earlier, still-applicable patch untouched.
    patches = [
        make_patch("PIPR", {"Country": "FRA", "Sector": "Consumer Discretionary"}),
        make_patch("PIPR", {"Country": "USA", "Conviction": "High"}),
    ]

    resolved = Engine().resolve(patches).patch_groups["PIPR"]

    assert len(resolved) == 1
    assert resolved[0].values == {
        "Country": "USA",
        "Sector": "Consumer Discretionary",
        "Conviction": "High",
    }


def test_nan_values_are_ignored_when_applying_patches():
    patches = [
        make_patch("JBL", {"Country": "USA", "Conviction": nan}),
    ]

    resolved = Engine().resolve(patches).patch_groups["JBL"]

    assert "Conviction" not in resolved[0].values


def test_none_values_are_ignored_when_applying_patches():
    patches = [
        make_patch("JBL", {"Country": "USA", "Conviction": None}),
    ]

    resolved = Engine().resolve(patches).patch_groups["JBL"]

    assert "Conviction" not in resolved[0].values


def test_keys_are_resolved_independently():
    patches = [
        make_patch("JBL", {"Country": "USA"}),
        make_patch("PIPR", {"Country": "FRA"}, begin=date(2024, 3, 1)),
    ]

    outcome = Engine().resolve(patches)

    assert set(outcome.patch_groups) == {"JBL", "PIPR"}
    assert len(outcome.patch_groups["JBL"]) == 1
    assert len(outcome.patch_groups["PIPR"]) == 1
    assert outcome.patch_groups["PIPR"][0].begin_date == date(2024, 3, 1)


def test_resolved_periods_are_contiguous_and_chronological():
    patches = [
        make_patch("FR", {"Country": "USA"}),
        make_patch("FR", {"Conviction": "Low"}, begin=date(2024, 2, 1)),
        make_patch("FR", {"Conviction": "Medium"}, begin=date(2024, 3, 1)),
    ]

    resolved = Engine().resolve(patches).patch_groups["FR"]

    assert len(resolved) == 3
    for earlier, later in pairwise(resolved):
        assert earlier.end_date == later.begin_date - timedelta(days=1)


def test_outcome_columns_include_fields_that_are_always_blank():
    # "Conviction" is NaN for every patch, so it never appears in any
    # resolved Patch.values, but the column still exists in the source
    # file and must show up in Outcome.columns.
    patches = [
        make_patch("JBL", {"Country": "USA", "Conviction": nan}),
    ]

    outcome = Engine().resolve(patches)

    assert outcome.columns == ["Conviction", "Country"]


def test_outcome_columns_union_across_all_keys():
    patches = [
        make_patch("JBL", {"Country": "USA"}),
        make_patch("PIPR", {"Sector": "Computers"}),
    ]

    outcome = Engine().resolve(patches)

    assert outcome.columns == ["Country", "Sector"]


def test_end_to_end_resolution_from_csv(tmp_path):
    csv_path = tmp_path / "patch.csv"
    csv_path.write_text(
        "BeginDate,EndDate,Issuer,Country,Conviction,Industry,Sector\n"
        ",,JBL,USA,,,Computers\n"
        ",,PIPR,FRA,,,Consumer Discretionary\n"
        ",,FR,USA,,,\n"
        "20240201,,FR,FRA,Low,,\n"
        ",,PIPR,USA,High,,\n"
    )

    rows = CSVReader().read(str(csv_path))
    patches = [Patch.from_patch_row(row) for row in rows]
    outcome = Engine().resolve(patches)

    jbl = outcome.patch_groups["JBL"]
    assert len(jbl) == 1
    assert jbl[0].values == {"Country": "USA", "Sector": "Computers"}

    pipr = outcome.patch_groups["PIPR"]
    assert len(pipr) == 1
    assert pipr[0].values == {
        "Country": "USA",
        "Sector": "Consumer Discretionary",
        "Conviction": "High",
    }

    fr = outcome.patch_groups["FR"]
    assert len(fr) == 2
    assert fr[0].values == {"Country": "USA"}
    assert fr[0].end_date == date(2024, 1, 31)
    assert fr[1].values == {"Country": "FRA", "Conviction": "Low"}
    assert fr[1].begin_date == date(2024, 2, 1)
