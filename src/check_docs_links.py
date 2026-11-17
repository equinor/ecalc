"""
Check that every DocsPage referenced from libecalc errors exists in the built docs.

Run after generating and building the docs:

    docs/scripts/generate-docs.sh && (cd docs && npm run build) && uv run python src/check_docs_links.py docs/build
"""

import argparse
import sys
from pathlib import Path

from libecalc.common.errors.docs_reference import DocsPage


def built_page_exists(build_directory: Path, page: DocsPage) -> bool:
    page_directory = build_directory / "docs" / page.value
    return (page_directory / "index.html").is_file() or page_directory.with_suffix(".html").is_file()


def find_missing_pages(build_directory: Path) -> list[DocsPage]:
    return [page for page in DocsPage if not built_page_exists(build_directory, page)]


def main(build_directory: Path) -> int:
    if not (build_directory / "docs").is_dir():
        print(f"No built docs in '{build_directory}'. Build the docs first.", file=sys.stderr)
        return 1

    missing = find_missing_pages(build_directory)
    for page in missing:
        print(f"DocsPage.{page.name} ('{page.value}') is not a page in the built docs.", file=sys.stderr)
    if missing:
        return 1

    print(f"All {len(DocsPage)} docs pages referenced from libecalc exist.")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check that the docs pages referenced from libecalc errors exist.")
    parser.add_argument("build_directory", type=Path, help="The docs build directory, e.g. docs/build.")
    sys.exit(main(parser.parse_args().build_directory))
