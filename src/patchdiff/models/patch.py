
from dataclasses import dataclass
from datetime import date
from typing import Any, Tuple

from patchdiff.models.row import PatchRow


def _key_field(extra: dict[str, Any]) -> str:
    if not extra:
        raise ValueError("Patch row must contain a key field")
    return next(iter(extra))


@dataclass
class Patch:
    begin_date: date
    end_date: date

    # key_field: str
    key_value: Any

    values: dict[str, Any]


    def in_period(self, begin_date, end_date):
        return self.begin_date <= end_date and self.end_date >= begin_date

    def applies(self, begin_date, end_date):
        return self.begin_date <= begin_date and self.end_date >= end_date

    @classmethod
    def from_patch_row(cls, row: PatchRow):
        extra = row.model_extra or {}
        key_field = _key_field(extra)
        key_value = extra[key_field]

        values = {
            field: value
            for field, value in row.model_extra.items()
            if field != key_field
            and value != None
        }

        return Patch(
            begin_date=row.begin_date,
            end_date=row.end_date,
            # key_field=key_field,
            key_value=key_value,
            values=values
        )
