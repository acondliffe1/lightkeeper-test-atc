import typer

from patchdiff.engine.comparator import Comparator
from patchdiff.engine.engine import Engine
from patchdiff.input.base import BaseReader
from patchdiff.input.factory import BaseReaderFactory
from patchdiff.models.patch import Patch
from patchdiff.output.reporting import ComparisonReporter

app = typer.Typer()

@app.command()
def main(original_path: str, new_path: str):
    original_reader: BaseReader = BaseReaderFactory.create_reader(original_path)
    new_reader: BaseReader = BaseReaderFactory.create_reader(new_path)


    original_patch_rows = original_reader.read(original_path)
    new_patch_rows = new_reader.read(new_path)

    original_patches = [Patch.from_patch_row(row) for row in original_patch_rows]
    new_patches = [Patch.from_patch_row(row) for row in new_patch_rows]

    # if original_patch.key_column != new_patch.key_column:
    #     raise ("Key columns are not the same!")

    engine: Engine = Engine()
    original_outcome = engine.resolve(original_patches)
    new_outcome = engine.resolve(new_patches)

    comparator: Comparator = Comparator()
    result = comparator.compare(original_outcome, new_outcome)

    ComparisonReporter().render(
        result, original_label=original_path, new_label=new_path
    )


if __name__ == "__main__":
    app()