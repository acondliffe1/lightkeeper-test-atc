from datetime import date

from rich.console import Console

from patchdiff.models.comparison import ComparisonResult, PatchChange, ValueChange
from patchdiff.models.row import BEGINNING_OF_TIME, END_OF_TIME
from patchdiff.output.reporting import ComparisonReporter

BOT = BEGINNING_OF_TIME
EOT = END_OF_TIME


def render(result: ComparisonResult, **kwargs) -> str:
    console = Console(record=True, force_terminal=False, width=100)
    ComparisonReporter(console=console).render(result, **kwargs)
    return console.export_text()


def test_no_changes_message():
    output = render(ComparisonResult(changes=[]))

    assert "No differences found" in output


def test_renders_key_field_and_values():
    result = ComparisonResult(
        changes=[
            PatchChange(
                key="FR",
                begin_date=date(2024, 2, 1),
                end_date=EOT,
                changes=[ValueChange("Conviction", None, "Low")],
            )
        ]
    )

    output = render(result)

    assert "FR" in output
    assert "Conviction" in output
    assert "Low" in output
    assert "2024-02-01" in output
    # open-ended dates are rendered with a placeholder, not the sentinel year
    assert "9999" not in output


def test_renders_labels_in_header():
    output = render(
        ComparisonResult(changes=[]),
        original_label="a.csv",
        new_label="b.csv",
    )

    assert "a.csv" in output
    assert "b.csv" in output


def test_summary_counts():
    result = ComparisonResult(
        changes=[
            PatchChange(
                key="FR",
                begin_date=BOT,
                end_date=EOT,
                changes=[
                    ValueChange("Country", "USA", "FRA"),
                    ValueChange("Conviction", None, "Low"),
                ],
            ),
            PatchChange(
                key="IBM",
                begin_date=BOT,
                end_date=EOT,
                changes=[ValueChange("Country", "USA", None)],
            ),
        ]
    )

    output = render(result)

    assert "2" in output  # 2 keys changed
    assert "3" in output  # 3 field changes total


def test_multiple_keys_are_sorted_alphabetically():
    result = ComparisonResult(
        changes=[
            PatchChange("IBM", BOT, EOT, [ValueChange("Country", "USA", "FRA")]),
            PatchChange("FR", BOT, EOT, [ValueChange("Country", "USA", "FRA")]),
        ]
    )

    output = render(result)

    assert output.index("FR") < output.index("IBM")


def test_column_changes_section_renders_added():
    output = render(ComparisonResult(changes=[], added_columns={"Analyst"}))

    assert "Analyst" in output
    assert "Added" in output
    assert "No differences found" not in output


def test_column_changes_section_renders_removed():
    output = render(ComparisonResult(changes=[], removed_columns={"Industry"}))

    assert "Industry" in output
    assert "Removed" in output
    assert "No differences found" not in output


def test_summary_mentions_column_counts():
    output = render(
        ComparisonResult(
            changes=[], added_columns={"Analyst"}, removed_columns={"Industry"}
        )
    )

    assert "1" in output
    assert "column(s) added" in output
    assert "column(s) removed" in output


def test_column_changes_section_precedes_key_tables():
    result = ComparisonResult(
        changes=[
            PatchChange("FR", BOT, EOT, [ValueChange("Country", "USA", "FRA")])
        ],
        added_columns={"Analyst"},
    )

    output = render(result)

    assert output.index("Columns") < output.index("FR")


def test_values_containing_markup_like_text_are_not_interpreted():
    result = ComparisonResult(
        changes=[
            PatchChange(
                key="FR",
                begin_date=BOT,
                end_date=EOT,
                changes=[ValueChange("Analyst", "Bob", "[red]Sally[/red]")],
            )
        ]
    )

    output = render(result)

    assert "[red]Sally[/red]" in output
