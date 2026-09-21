
from dataclasses import dataclass

from patchdiff.models.patch import Patch


@dataclass
class Outcome:
    patch_groups: dict[str,list[Patch]]
    columns: list[str]
    