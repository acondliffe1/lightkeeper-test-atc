import pandas as pd
from pydantic import ValidationError
from patchdiff.input.base import BaseReader
from patchdiff.models.row import PatchRow


class CSVReader(BaseReader):

    def read(self, path: str) -> list[PatchRow]:
        df = pd.read_csv(path)

        return [
            PatchRow.model_validate(row.to_dict())
            for _, row in df.iterrows()
        ]
        
