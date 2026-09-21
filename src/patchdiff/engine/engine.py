from collections import defaultdict
from dataclasses import replace
from datetime import date, timedelta
from math import isnan

from patchdiff.models.outcome import Outcome
from patchdiff.models.patch import Patch
from patchdiff.utils import determine_periods


class Engine:

    def _apply_patches(self, patches: list[Patch]):
        state = {}
        for patch in patches:
            for key, value in patch.values.items():
                if value is None or (isinstance(value, float) and isnan(value)):
                    continue
                state[key] = value
        return state

    def _group_patches_by_key(self, rows: list[Patch]) -> dict[str, list[Patch]]:
        groups = defaultdict(list)
        for row in rows:
            key = row.key_value
            groups[key].append(row)
        return groups

    def _resolve_patches(self, patches: list[Patch]) -> list[Patch]:           
        periods = determine_periods(patches)
        resolved: list[Patch] = []
        for begin_date, end_date in periods:
            applicable = [
                patch
                for patch in patches
                if patch.in_period(begin_date, end_date)
            ]

            if not applicable:
                continue
                # print (f"{key} has applicable patches {applicable} in period {begin_date}->{end_date}")

            state = self._apply_patches(applicable)

            resolved.append(
                Patch(
                    begin_date=begin_date,
                    end_date=end_date,
                    # key_field=grouped_patch[0].key_field,
                    key_value=patches[0].key_value,
                    values=state
                )
            )
        return resolved

    def _column_schema(self, patches: list[Patch]) -> list[str]:
        columns: set[str] = set()
        for patch in patches:
            columns.update(patch.values.keys())
        return sorted(columns)

    def resolve(self, patches: list[Patch]) -> Outcome:
        grouped_patches = self._group_patches_by_key(patches)

        resolved: dict[str, list[Patch]] = {}

        for key, group in grouped_patches.items():
            resolved[key] = self._resolve_patches(group)

        return Outcome(patch_groups=resolved, columns=self._column_schema(patches))



