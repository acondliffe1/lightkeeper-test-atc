from abc import ABC, abstractmethod

from patchdiff.models.row import PatchRow

class BaseReader(ABC):
    @abstractmethod
    def read(self, path) -> list[PatchRow]:
        pass