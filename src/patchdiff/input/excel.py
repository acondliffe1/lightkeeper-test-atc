from patchdiff.input.base import BaseReader
from patchdiff.models.row import PatchRow


class ExcelReader(BaseReader):

    def read(self, path: str) -> list[PatchRow]:
        raise ("Not yet Implemented")
        
