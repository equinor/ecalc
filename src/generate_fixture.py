import argparse
from pathlib import Path

from libecalc.fixtures.cases.nextgen.reference_model import (
    export_example_archive,
    export_example_pages,
    export_reference_model,
)
from libecalc.presentation.yaml.yaml_types.yaml_version import LATEST_YAML_VERSION

DEFAULT_OUTPUT_DIRECTORY = Path(__file__).parent / "libecalc" / "examples" / "nextgen"
DEFAULT_DOCS_DIRECTORY = Path(__file__).parent.parent / "docs" / "docs" / "about" / "nextgen" / "examples"
DEFAULT_ARCHIVE_DIRECTORY = Path(__file__).parent.parent / "docs" / "static" / "examples" / "nextgen"


def main(
    yaml_version: int = LATEST_YAML_VERSION,
    output_directory: Path = DEFAULT_OUTPUT_DIRECTORY,
    docs_directory: Path = DEFAULT_DOCS_DIRECTORY,
    archive_directory: Path = DEFAULT_ARCHIVE_DIRECTORY,
) -> None:
    generated_paths = [
        *export_reference_model(output_directory, yaml_version),
        export_example_archive(archive_directory, output_directory, yaml_version),
        *export_example_pages(docs_directory, yaml_version),
    ]
    for path in generated_paths:
        print(f"Generated: {path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate the nextgen example model and its documentation page.")
    parser.add_argument(
        "--yaml-version",
        type=int,
        default=LATEST_YAML_VERSION,
        choices=range(1, LATEST_YAML_VERSION + 1),
        help="YAML version to generate. Defaults to the latest version.",
    )
    parser.add_argument("--output-directory", type=Path, default=DEFAULT_OUTPUT_DIRECTORY)
    parser.add_argument("--docs-directory", type=Path, default=DEFAULT_DOCS_DIRECTORY)
    parser.add_argument("--archive-directory", type=Path, default=DEFAULT_ARCHIVE_DIRECTORY)
    arguments = parser.parse_args()
    main(arguments.yaml_version, arguments.output_directory, arguments.docs_directory, arguments.archive_directory)
