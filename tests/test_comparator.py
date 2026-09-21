from datetime import date

from patchdiff.engine.comparator import Comparator
from patchdiff.engine.engine import Engine
from patchdiff.input.csv import CSVReader
from patchdiff.models.comparison import PatchChange
from patchdiff.models.outcome import Outcome
from patchdiff.models.patch import Patch
from patchdiff.models.row import BEGINNING_OF_TIME, END_OF_TIME

BOT = BEGINNING_OF_TIME
EOT = END_OF_TIME


def patch(key, values, begin=BOT, end=EOT):
    return Patch(begin_date=begin, end_date=end, key_value=key, values=values)


def outcome(columns, **groups):
    return Outcome(patch_groups=groups, columns=sorted(columns))


def field_changes(patch_change: PatchChange) -> dict[str, tuple]:
    return {
        change.field: (change.original_value, change.new_value)
        for change in patch_change.changes
    }


def test_identical_outcomes_produce_no_changes():
    original = outcome({"Country"}, FR=[patch("FR", {"Country": "USA"})])
    new = outcome({"Country"}, FR=[patch("FR", {"Country": "USA"})])

    result = Comparator().compare(original, new)

    assert result.changes == []


def test_detects_modified_field():
    original = outcome({"Country"}, FR=[patch("FR", {"Country": "USA"})])
    new = outcome({"Country"}, FR=[patch("FR", {"Country": "FRA"})])

    result = Comparator().compare(original, new)

    assert len(result.changes) == 1
    change = result.changes[0]
    assert change.key == "FR"
    assert (change.begin_date, change.end_date) == (BOT, EOT)
    assert field_changes(change) == {"Country": ("USA", "FRA")}


def test_detects_added_field():
    # "Conviction" exists in both files' schemas but only gets a value in
    # the new one -- a value-level change, not a schema-level column add.
    columns = {"Country", "Conviction"}
    original = outcome(columns, FR=[patch("FR", {"Country": "USA"})])
    new = outcome(columns, FR=[patch("FR", {"Country": "USA", "Conviction": "Low"})])

    result = Comparator().compare(original, new)

    assert field_changes(result.changes[0]) == {"Conviction": (None, "Low")}


def test_detects_removed_field():
    columns = {"Country", "Conviction"}
    original = outcome(
        columns, FR=[patch("FR", {"Country": "USA", "Conviction": "Low"})]
    )
    new = outcome(columns, FR=[patch("FR", {"Country": "USA"})])

    result = Comparator().compare(original, new)

    assert field_changes(result.changes[0]) == {"Conviction": ("Low", None)}


def test_detects_key_added_only_in_new():
    original = outcome({"Country"}, FR=[patch("FR", {"Country": "USA"})])
    new = outcome(
        {"Country"},
        FR=[patch("FR", {"Country": "USA"})],
        IBM=[patch("IBM", {"Country": "USA"})],
    )

    result = Comparator().compare(original, new)

    assert len(result.changes) == 1
    assert result.changes[0].key == "IBM"
    assert field_changes(result.changes[0]) == {"Country": (None, "USA")}


def test_detects_key_removed_only_in_original():
    original = outcome(
        {"Country"},
        FR=[patch("FR", {"Country": "USA"})],
        IBM=[patch("IBM", {"Country": "USA"})],
    )
    new = outcome({"Country"}, FR=[patch("FR", {"Country": "USA"})])

    result = Comparator().compare(original, new)

    assert len(result.changes) == 1
    assert result.changes[0].key == "IBM"
    assert field_changes(result.changes[0]) == {"Country": ("USA", None)}


def test_no_changes_when_only_period_boundaries_differ():
    # original has one continuous patch; new re-slices the exact same
    # values across two periods. The union of periods differs, but no
    # field actually changed, so there should be no reported changes.
    original = outcome({"Country"}, FR=[patch("FR", {"Country": "USA"})])
    new = outcome(
        {"Country"},
        FR=[
            patch("FR", {"Country": "USA"}, begin=BOT, end=date(2024, 1, 31)),
            patch("FR", {"Country": "USA"}, begin=date(2024, 2, 1), end=EOT),
        ],
    )

    result = Comparator().compare(original, new)

    assert result.changes == []


def test_change_localized_to_correct_period_when_splits_differ():
    columns = {"Country", "Conviction"}
    original = outcome(columns, FR=[patch("FR", {"Country": "USA"})])
    new = outcome(
        columns,
        FR=[
            patch("FR", {"Country": "USA"}, begin=BOT, end=date(2024, 1, 31)),
            patch(
                "FR",
                {"Country": "USA", "Conviction": "Low"},
                begin=date(2024, 2, 1),
                end=EOT,
            ),
        ],
    )

    result = Comparator().compare(original, new)

    assert len(result.changes) == 1
    change = result.changes[0]
    assert (change.begin_date, change.end_date) == (date(2024, 2, 1), EOT)
    assert field_changes(change) == {"Conviction": (None, "Low")}


def test_added_column_still_reported_at_row_level():
    # The "Columns" summary flags Analyst as a wholesale addition, but a
    # key that actually got a value for it should still show that value
    # in the normal per-row diff -- the summary is additive, not a
    # replacement for the row-level detail.
    original = outcome({"Country"}, FR=[patch("FR", {"Country": "USA"})])
    new = outcome(
        {"Country", "Analyst"},
        FR=[patch("FR", {"Country": "USA", "Analyst": "Bob"})],
    )

    result = Comparator().compare(original, new)

    assert len(result.changes) == 1
    assert field_changes(result.changes[0]) == {"Analyst": (None, "Bob")}
    assert result.added_columns == {"Analyst"}
    assert result.removed_columns == set()


def test_removed_column_still_reported_at_row_level():
    original = outcome(
        {"Country", "Analyst"},
        FR=[patch("FR", {"Country": "USA", "Analyst": "Bob"})],
    )
    new = outcome({"Country"}, FR=[patch("FR", {"Country": "USA"})])

    result = Comparator().compare(original, new)

    assert len(result.changes) == 1
    assert field_changes(result.changes[0]) == {"Analyst": ("Bob", None)}
    assert result.removed_columns == {"Analyst"}
    assert result.added_columns == set()


def test_common_column_diff_reported_alongside_added_column():
    original = outcome({"Country"}, FR=[patch("FR", {"Country": "USA"})])
    new = outcome(
        {"Country", "Analyst"},
        FR=[patch("FR", {"Country": "FRA", "Analyst": "Bob"})],
    )

    result = Comparator().compare(original, new)

    assert len(result.changes) == 1
    assert field_changes(result.changes[0]) == {
        "Country": ("USA", "FRA"),
        "Analyst": (None, "Bob"),
    }
    assert result.added_columns == {"Analyst"}


def test_added_removed_columns_detected_even_with_no_keys():
    original = outcome({"Country", "Industry"})
    new = outcome({"Country", "Analyst"})

    result = Comparator().compare(original, new)

    assert result.changes == []
    assert result.added_columns == {"Analyst"}
    assert result.removed_columns == {"Industry"}


def test_end_to_end_column_addition_from_csv():
    # input/Patch2.csv adds an "Analyst" column vs input/Patch1.csv, with a
    # real value ("Bob") for FR starting 2024-02-01. That should surface
    # both as a schema-level "Columns" entry AND as a normal row-level
    # field change for FR.
    original_rows = CSVReader().read("input/Patch1.csv")
    new_rows = CSVReader().read("input/Patch2.csv")

    original_outcome = Engine().resolve(
        [Patch.from_patch_row(row) for row in original_rows]
    )
    new_outcome = Engine().resolve([Patch.from_patch_row(row) for row in new_rows])

    result = Comparator().compare(original_outcome, new_outcome)

    assert result.added_columns == {"Analyst"}

    fr_analyst_changes = [
        value_change
        for change in result.changes
        if change.key == "FR"
        for value_change in change.changes
        if value_change.field == "Analyst"
    ]
    assert len(fr_analyst_changes) == 1
    assert (fr_analyst_changes[0].original_value, fr_analyst_changes[0].new_value) == (
        None,
        "Bob",
    )
