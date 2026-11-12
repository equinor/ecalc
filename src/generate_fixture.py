import argparse
from pathlib import Path

from libecalc.fixtures.cases.nextgen.reference_model import export_example_pages, export_reference_models

DEFAULT_OUTPUT_DIRECTORY = Path(__file__).parent / "libecalc" / "examples" / "nextgen"
DEFAULT_DOCS_DIRECTORY = Path(__file__).parent.parent / "docs" / "docs" / "about" / "nextgen" / "examples"


def main(
    output_directory: Path = DEFAULT_OUTPUT_DIRECTORY,
    docs_directory: Path = DEFAULT_DOCS_DIRECTORY,
    include_previous: bool = False,
) -> None:
    generated_paths = [
        *export_reference_models(output_directory, include_previous),
        *export_example_pages(docs_directory, include_previous),
    ]
    for path in generated_paths:
        print(f"Generated: {path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate the nextgen example models and their documentation pages.")
    parser.add_argument("--output-directory", type=Path, default=DEFAULT_OUTPUT_DIRECTORY)
    parser.add_argument("--docs-directory", type=Path, default=DEFAULT_DOCS_DIRECTORY)
    parser.add_argument(
        "--include-previous",
        action="store_true",
        help="Also regenerate the previous YAML version. By default only the current version is generated.",
    )
    arguments = parser.parse_args()
    main(arguments.output_directory, arguments.docs_directory, arguments.include_previous)
