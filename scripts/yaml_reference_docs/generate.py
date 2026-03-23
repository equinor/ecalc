"""
Entry point: generate the YAML reference page from eCalc Pydantic models.

Writes a single Markdown file to docs/docs/about/generated-yaml/.

Usage:
    python -m scripts.yaml_reference_docs.generate
"""

from __future__ import annotations

from pathlib import Path

from libecalc.presentation.yaml.yaml_types.components.yaml_asset import YamlAsset
from .render_markdown import render_full_page
from .keyword_tree import KeywordTreeBuilder


OUT_DIR = Path("docs/docs/about/yaml_overview")

# Top-level keywords to exclude from generated docs.
# These are part of the ongoing refactoring and not yet available to users.
# Remove from this set as each keyword becomes production-ready.
EXCLUDED_TOP_LEVEL_KEYWORDS: set[str] = {
    "FLUID_MODELS",
    "PROCESS_UNITS",
    "PROCESS_SYSTEMS",
    "PROCESS_SIMULATIONS",
    "INLET_STREAMS",
}


def main() -> None:
    tree = KeywordTreeBuilder().build(root_model=YamlAsset, exclude_top_level=EXCLUDED_TOP_LEVEL_KEYWORDS)
    page = render_full_page(tree)

    out_file = OUT_DIR / "index.md"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(page, encoding="utf-8")
    print(f"Wrote {out_file} ({len(page)} chars)")


if __name__ == "__main__":
    main()
