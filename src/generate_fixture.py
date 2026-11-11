import argparse
from pathlib import Path

from libecalc.fixtures.cases.nextgen.reference_model import export_reference_model

DEFAULT_OUTPUT_DIRECTORY = Path(__file__).parent / "libecalc" / "examples" / "nextgen"


def main(output_directory: Path = DEFAULT_OUTPUT_DIRECTORY) -> None:
    for path in export_reference_model(output_directory):
        print(f"Generated: {path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate the nextgen example model from the reference model.")
    parser.add_argument("--output-directory", type=Path, default=DEFAULT_OUTPUT_DIRECTORY)
    main(parser.parse_args().output_directory)
