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


def main() -> None:
    tree = KeywordTreeBuilder().build(YamlAsset)
    page = render_full_page(tree)

    out_file = OUT_DIR / "index.md"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(page, encoding="utf-8")
    print(f"Wrote {out_file} ({len(page)} chars)")


if __name__ == "__main__":
    main()
