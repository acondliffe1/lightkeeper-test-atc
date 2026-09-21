
from dataclasses import dataclass, field
from datetime import date
from typing import Any


@dataclass
class ComparisonResult:
    changes: list[PatchChange]
    added_columns: set[str] = field(default_factory=set)
    removed_columns: set[str] = field(default_factory=set)

@dataclass
class PatchChange:
    key: str
    begin_date: date
    end_date: date
    changes: list[ValueChange]

@dataclass
class ValueChange:
    field: str
    original_value: Any
    new_value: Any

