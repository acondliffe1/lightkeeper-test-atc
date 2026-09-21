
from patchdiff.models.comparison import ComparisonResult, PatchChange, ValueChange
from patchdiff.models.outcome import Outcome
from patchdiff.models.patch import Patch
from patchdiff.utils import determine_periods


class Comparator:

    def compare(self, original_outcome: Outcome, new_outcome: Outcome):
        original_columns = set(original_outcome.columns)
        new_columns = set(new_outcome.columns)

        added_columns = new_columns - original_columns
        removed_columns = original_columns - new_columns

        changes = []

        shared_keys = original_outcome.patch_groups.keys() | new_outcome.patch_groups.keys()

        for key in shared_keys:
            original_patches = original_outcome.patch_groups.get(key, [])
            new_patches = new_outcome.patch_groups.get(key, [])

            changes.extend(self._compare_key(key, original_patches, new_patches))

        return ComparisonResult(
            changes=changes,
            added_columns=added_columns,
            removed_columns=removed_columns,
        )

    def _compare_key(
        self,
        key,
        original_patches: list[Patch],
        new_patches: list[Patch],
    ):
        periods = determine_periods(original_patches + new_patches)

        patch_changes = []

        for begin_date, end_date in periods:
            original_patch = self._find_patch(original_patches, begin_date, end_date)
            new_patch = self._find_patch(new_patches, begin_date, end_date)

            original_values = original_patch.values if original_patch else {}
            new_values = new_patch.values if new_patch else {}

            fields = original_values.keys() | new_values.keys()

            value_changes = []

            for field in fields:
                original_value = original_values.get(field)
                new_value = new_values.get(field)

                if original_value != new_value:
                    value_changes.append(
                        ValueChange(field, original_value, new_value)
                    )
            if value_changes:
                patch_changes.append(
                    PatchChange(key, begin_date, end_date, value_changes)
                )
        return patch_changes

    def _find_patch(self, patches: list[Patch], begin_date, end_date):
        for patch in patches:
            if patch.applies(begin_date, end_date):
                return patch
        return None

