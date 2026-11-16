import argparse
from pathlib import Path

from libecalc.fixtures.cases.nextgen.reference_model import (
    export_example_archive,
    export_example_page,
    export_reference_model,
)

DEFAULT_OUTPUT_DIRECTORY = Path(__file__).parent / "libecalc" / "examples" / "nextgen"
DEFAULT_DOCS_DIRECTORY = Path(__file__).parent.parent / "docs" / "docs" / "about" / "nextgen"
DEFAULT_ARCHIVE_DIRECTORY = Path(__file__).parent.parent / "docs" / "static" / "examples" / "nextgen"


def main(
    output_directory: Path = DEFAULT_OUTPUT_DIRECTORY,
    docs_directory: Path = DEFAULT_DOCS_DIRECTORY,
    archive_directory: Path = DEFAULT_ARCHIVE_DIRECTORY,
) -> None:
    generated_paths = [
        *export_reference_model(output_directory),
        export_example_archive(archive_directory, output_directory),
        export_example_page(docs_directory),
    ]
    for path in generated_paths:
        print(f"Generated: {path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate the nextgen example model for the latest YAML version, its documentation page and archive."
    )
    parser.add_argument("--output-directory", type=Path, default=DEFAULT_OUTPUT_DIRECTORY)
    parser.add_argument("--docs-directory", type=Path, default=DEFAULT_DOCS_DIRECTORY)
    parser.add_argument("--archive-directory", type=Path, default=DEFAULT_ARCHIVE_DIRECTORY)
    arguments = parser.parse_args()
    main(arguments.output_directory, arguments.docs_directory, arguments.archive_directory)
