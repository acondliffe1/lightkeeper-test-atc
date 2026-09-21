# patchdiff

`patchdiff` reconciles two "patch" files describing time-sliced changes to a
set of records (e.g. security master overrides keyed by issuer) and reports
what changed between them, field by field, period by period.

A patch file is a table where each row says "starting on `BeginDate` (and
until `EndDate`), this key had these field values." Rows accumulate over
time — a later row only overrides the specific fields it sets, not the
whole record. `patchdiff` resolves each patch file into the actual
point-in-time state of every key across history, then diffs the two
resolutions against each other and prints a report.

## Patch file format

CSV (Excel is planned, see [Known limitations](#known-limitations)) with
these columns:

| Column                      | Meaning                                                                 |
| ---------------------------- | ------------------------------------------------------------------------ |
| `BeginDate` (optional)       | `YYYYMMDD`. Blank means "since the beginning of time".                  |
| `EndDate` (optional)         | `YYYYMMDD`. Blank means "until the end of time".                        |
| *first remaining column*     | The **key** the row applies to (e.g. `Issuer`). Whatever column comes first after the two date columns is treated as the key — there's no separate config for it. |
| *any other columns*          | Attribute values patched onto that key for the given date range. Blank cells are ignored (they don't overwrite a previously-set value). |

Example (`input/Patch1.csv`):

```csv
BeginDate,EndDate,Issuer,Country,Conviction,Industry,Sector
,,JBL,USA,,,Computers
,,PIPR,FRA,,,Consumer Discretionary
,,FR,USA,,,
20240201,,FR,FRA,Low,,
,,PIPR,USA,High,,
```

Resolving this file produces:

- **JBL**: `USA` / `Computers`, for all time.
- **PIPR**: one row set `Country=FRA, Sector=Consumer Discretionary`, another
  set `Country=USA, Conviction=High`. Merged, PIPR is `Country=USA,
  Sector=Consumer Discretionary, Conviction=High` for all time (later row
  wins per-field, doesn't blank out fields it didn't mention).
- **FR**: `Country=USA` from the beginning of time through 2024-01-31, then
  `Country=FRA, Conviction=Low` from 2024-02-01 onward.

## Installation

Requires Python 3.14+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
```

## Usage

```bash
uv run patchdiff <original.csv> <new.csv>
```

This reads both files, resolves each into per-key, per-period state, diffs
them, and prints a report. For example:

```
$ uv run patchdiff input/Patch0.csv input/Patch4.csv
-------------------- input/Patch0.csv vs input/Patch4.csv ---------------------
Columns
+------------------+
| Change | Column  |
|--------+---------|
| Added  | Analyst |
+------------------+
FR
+-------------------------------------------------+
| Period            | Field      | Before | After |
|-------------------+------------+--------+-------|
| 2024-02-01 -> ... | Analyst    | -      | Sally |
|                   | Conviction | -      | Low   |
|                   | Country    | USA    | FRA   |
+-------------------------------------------------+
IBM
+-------------------------------------------------+
| Period            | Field      | Before | After |
|-------------------+------------+--------+-------|
| 2024-03-01 -> ... | Conviction | -      | Low   |
+-------------------------------------------------+
PIPR
+------------------------------------------+
| Period     | Field      | Before | After |
|------------+------------+--------+-------|
| ... -> ... | Conviction | -      | High  |
|            | Country    | FRA    | USA   |
+------------------------------------------+

3 key(s) changed across 3 period(s), 6 field change(s). 1 column(s) added, 0
column(s) removed.
```

A field going from a real value to `-` means it was removed; from `-` to a
real value means it was added; a key that only appears on one side shows up
the same way, with every one of its fields changing from/to `-`. A column
that's entirely new or entirely gone (not in the other file's header at
all — like `Analyst` above, which `Patch0.csv` doesn't have) is additionally
called out once in its own "Columns" section — that section is a summary on
top of the row-level detail, not a replacement for it, so a key that
genuinely got a new value still shows it in its own table too. Output is
colorized (red/green) in an interactive terminal.

## Architecture

```
src/patchdiff/
├── input/          # File readers
│   ├── base.py       BaseReader ABC
│   ├── csv.py        CSVReader — implemented, backed by pandas
│   ├── excel.py       ExcelReader — not yet implemented
│   └── factory.py     BaseReaderFactory — picks a reader by file extension
├── models/
│   ├── row.py        PatchRow — pydantic model, validates/normalizes one raw row
│   ├── patch.py       Patch — domain object derived from a PatchRow (dataclass)
│   ├── outcome.py      Outcome — a resolved patch file: key -> list[Patch], plus the file's column schema (dataclass)
│   └── comparison.py    ComparisonResult / PatchChange / ValueChange — diff output model
├── engine/
│   ├── engine.py       Engine.resolve() — the core reconciliation logic
│   └── comparator.py    Comparator.compare() — diffs two Outcomes into a ComparisonResult
├── utils.py          determine_periods() — shared period-splitting logic
├── output/
│   └── reporting.py    ComparisonReporter — renders a ComparisonResult with rich
└── main.py           Typer CLI entry point
```

### `Engine.resolve`

Given a flat list of `Patch` objects:

1. Groups them by key value.
2. For each key, collects every distinct `begin_date`/`end_date` across its
   patches and turns them into a set of contiguous, non-overlapping
   periods spanning that key's whole history (`utils.determine_periods`).
3. For each period, finds the patches whose date range overlaps it and
   folds their field values together in list order (a later patch
   overwrites only the fields it sets; blank/`NaN`/`None` values never
   overwrite anything), producing one resolved `Patch` per period.
4. Separately, unions every input patch's field names (before any of that
   `NaN`-dropping) into `Outcome.columns` — the file's full column schema,
   including columns that are blank for every row.

The result is an `Outcome`: `{key: [resolved Patch, ...]}` plus `columns`,
with each key's patches in chronological order and no gaps or overlaps.

### `Comparator.compare`

Given two resolved `Outcome`s:

1. Diffs `original_outcome.columns` against `new_outcome.columns` to get
   `added_columns`/`removed_columns` — columns that exist in one file's
   header but not the other's at all. This is purely additional summary
   information; it doesn't suppress anything below.
2. For each key present in either side, merges both sides' period
   boundaries (`utils.determine_periods` again, over both sides' patches
   combined) so the two timelines are compared on a common set of periods
   — even if the original and new files split history at different dates.
3. For each merged period, looks up the resolved patch on each side that
   fully covers it and compares field values, regardless of whether the
   field belongs to a schema-level added/removed column or a column
   common to both files.
4. Emits one `ValueChange` per differing field (missing side = `None`,
   which naturally represents an added/removed value, or an added/removed
   key when every field differs), grouped into a `PatchChange` per
   key/period, collected into a `ComparisonResult` alongside the
   added/removed column sets.

### `ComparisonReporter`

Takes a `ComparisonResult` and renders it as [rich](https://rich.readthedocs.io/)
tables: a "Columns" table for any added/removed columns (when present),
followed by one table per changed key (columns: Period, Field, Before,
After), then a summary line — all sorted deterministically by
key/period/field/column. It only ever builds `rich.text.Text` objects
around data values (never string-interpolates them into markup), so field
names, column names, or values that happen to contain `[...]` render
literally instead of being misparsed as formatting.

## Known limitations

This is a work in progress. Current gaps (also pinned down by tests, so
fixing them is a deliberate, visible change rather than a silent behavior
swap):

- **`ExcelReader.read` is unimplemented**, and its `raise (...)`
  stub is itself broken (raising a plain string raises `TypeError`
  rather than a meaningful error) — `.xlsx`/`.xls` inputs cannot be read
  yet. See `tests/test_input_excel.py`.
- No validation that the two files being compared share the same key
  column/type.

## Testing

```bash
uv run pytest
```

Tests live under `tests/`, mirroring the `src/patchdiff` package layout:

- `test_models_row.py` — `PatchRow` date parsing/normalization and validation
- `test_models_patch.py` — `Patch.from_patch_row` and `Patch.in_period`
- `test_engine.py` — `Engine.resolve`, including an end-to-end CSV-to-`Outcome`
  case and `Outcome.columns` derivation
- `test_utils.py` — `determine_periods`
- `test_comparator.py` — `Comparator.compare`, including added/removed
  fields and keys (value-level) and added/removed columns (schema-level,
  with a real-fixture regression against `input/Patch1.csv`/`Patch2.csv`),
  plus periods split differently between the two sides
- `test_reporting.py` — `ComparisonReporter`, including the markup-safety
  behavior described above and the "Columns" section
- `test_input_csv.py` — `CSVReader`
- `test_input_excel.py` / `test_input_factory.py` — reader factory and the `ExcelReader` stub

## Development

```bash
uv sync --group dev   # installs pytest + ruff
uv run ruff check .   # lint
```
