from datetime import date

from rich.console import Console
from rich.table import Table
from rich.text import Text

from patchdiff.models.comparison import ComparisonResult, PatchChange
from patchdiff.models.row import BEGINNING_OF_TIME, END_OF_TIME


class ComparisonReporter:
    """Renders a ComparisonResult as a formatted terminal report."""

    def __init__(self, console: Console | None = None):
        self.console = console or Console()

    def render(
        self,
        result: ComparisonResult,
        *,
        original_label: str = "original",
        new_label: str = "new",
    ) -> None:
        changes_by_key = self._group_by_key(result.changes)
        has_column_changes = bool(result.added_columns or result.removed_columns)

        self.console.rule(
            Text.assemble(
                (original_label, "bold"), " vs ", (new_label, "bold")
            )
        )

        if not changes_by_key and not has_column_changes:
            self.console.print(Text("\nNo differences found.", style="green"))
            return

        if has_column_changes:
            self.console.print(self._build_column_changes_table(result))

        for key in sorted(changes_by_key):
            self.console.print(self._build_table(key, changes_by_key[key]))

        self._render_summary(changes_by_key, result.added_columns, result.removed_columns)

    def _group_by_key(
        self, changes: list[PatchChange]
    ) -> dict[str, list[PatchChange]]:
        grouped: dict[str, list[PatchChange]] = {}
        for change in changes:
            grouped.setdefault(change.key, []).append(change)

        for key_changes in grouped.values():
            key_changes.sort(key=lambda change: change.begin_date)

        return grouped

    def _build_column_changes_table(self, result: ComparisonResult) -> Table:
        table = Table(
            title=Text("Columns", style="bold cyan"),
            title_justify="left",
            header_style="bold",
        )
        table.add_column("Change")
        table.add_column("Column")

        for column in sorted(result.added_columns):
            table.add_row("Added", Text(str(column), style="green"))
        for column in sorted(result.removed_columns):
            table.add_row("Removed", Text(str(column), style="red"))

        return table

    def _build_table(self, key: str, patch_changes: list[PatchChange]) -> Table:
        table = Table(
            title=Text(str(key), style="bold cyan"),
            title_justify="left",
            header_style="bold",
        )
        table.add_column("Period")
        table.add_column("Field")
        table.add_column("Before")
        table.add_column("After")

        for patch_change in patch_changes:
            period = self._format_period(
                patch_change.begin_date, patch_change.end_date
            )
            value_changes = sorted(patch_change.changes, key=lambda c: c.field)

            for index, value_change in enumerate(value_changes):
                table.add_row(
                    period if index == 0 else "",
                    Text(str(value_change.field)),
                    self._format_value(value_change.original_value, style="red"),
                    self._format_value(value_change.new_value, style="green"),
                )

        return table

    def _format_period(self, begin_date: date, end_date: date) -> Text:
        begin = "..." if begin_date == BEGINNING_OF_TIME else begin_date.isoformat()
        end = "..." if end_date == END_OF_TIME else end_date.isoformat()
        return Text(f"{begin} -> {end}")

    def _format_value(self, value, *, style: str) -> Text:
        if value is None:
            return Text("-", style="dim")
        return Text(str(value), style=style)

    def _render_summary(
        self,
        changes_by_key: dict[str, list[PatchChange]],
        added_columns: set[str],
        removed_columns: set[str],
    ) -> None:
        sentences: list[Text] = []

        if changes_by_key:
            key_count = len(changes_by_key)
            period_count = sum(len(changes) for changes in changes_by_key.values())
            field_count = sum(
                len(patch_change.changes)
                for changes in changes_by_key.values()
                for patch_change in changes
            )

            sentences.append(
                Text.assemble(
                    (str(key_count), "bold"),
                    " key(s) changed across ",
                    (str(period_count), "bold"),
                    " period(s), ",
                    (str(field_count), "bold"),
                    " field change(s).",
                )
            )

        if added_columns or removed_columns:
            sentences.append(
                Text.assemble(
                    (str(len(added_columns)), "bold"),
                    " column(s) added, ",
                    (str(len(removed_columns)), "bold"),
                    " column(s) removed.",
                )
            )

        if not sentences:
            return

        summary = Text("\n")
        for index, sentence in enumerate(sentences):
            if index:
                summary.append(" ")
            summary.append(sentence)

        self.console.print(summary)
