import argparse
from pathlib import Path

from libecalc.fixtures.cases.nextgen.reference_model import (
    build_reference_model,
    example_files,
    export_example_archive,
    export_example_page,
)
from libecalc.presentation.yaml.yaml_types.yaml_version import LATEST_YAML_VERSION

DEFAULT_DOCS_DIRECTORY = Path(__file__).parent.parent / "docs" / "docs" / "about" / "nextgen"
DEFAULT_ARCHIVE_DIRECTORY = Path(__file__).parent.parent / "docs" / "static" / "examples" / "nextgen"


def main(
    docs_directory: Path = DEFAULT_DOCS_DIRECTORY,
    archive_directory: Path = DEFAULT_ARCHIVE_DIRECTORY,
) -> None:
    model = build_reference_model(LATEST_YAML_VERSION)
    files = example_files(model)
    generated_paths = [
        export_example_archive(archive_directory, files),
        export_example_page(docs_directory, model, files),
    ]
    for path in generated_paths:
        print(f"Generated: {path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate the nextgen example documentation page and archive for the latest YAML version."
    )
    parser.add_argument("--docs-directory", type=Path, default=DEFAULT_DOCS_DIRECTORY)
    parser.add_argument("--archive-directory", type=Path, default=DEFAULT_ARCHIVE_DIRECTORY)
    arguments = parser.parse_args()
    main(arguments.docs_directory, arguments.archive_directory)
