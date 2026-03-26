"""
Tests for the YAML reference page generator.

Verifies that the keyword tree, page model, and rendered Markdown
correctly cover all YAML keywords defined in the Pydantic models.
"""

from __future__ import annotations

import pytest
from pydantic import BaseModel, Field

from libecalc.presentation.yaml.yaml_types.components.yaml_asset import YamlAsset
from scripts.yaml_reference_docs.doc_model import PageDoc
from scripts.yaml_reference_docs.keyword_tree import KeywordNode, KeywordTreeBuilder
from scripts.yaml_reference_docs.page_builder import PageBuilder
from scripts.yaml_reference_docs.render_markdown import render_full_page

# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def root_node() -> KeywordNode:
    return KeywordTreeBuilder().build(YamlAsset)


@pytest.fixture(scope="module")
def page(root_node) -> PageDoc:
    return PageBuilder().build(root_node)


@pytest.fixture(scope="module")
def markdown(root_node) -> str:
    return render_full_page(root_node)


# ── Tests ─────────────────────────────────────────────────────────────────


def test_every_top_level_field_has_a_section(page):
    """Every YamlAsset field with a keyword title gets its own section."""
    section_keywords = {s.keyword for s in page.sections}
    for field_name, field_info in YamlAsset.model_fields.items():
        title = field_info.title or field_name.upper()
        if not title or not title.isupper():
            continue
        assert title in section_keywords, (
            f"YamlAsset.{field_name} (title='{title}') has no section. " f"Available: {sorted(section_keywords)}"
        )


def test_every_keyword_appears_in_output(root_node, markdown):
    """Every keyword in the tree appears somewhere in the rendered Markdown."""
    missing = []
    for node in root_node.walk():
        if node.keyword == "ROOT":
            continue
        if node.keyword not in markdown:
            missing.append("/".join(node.path))

    assert not missing, (
        f"{len(missing)} keyword(s) from schema tree missing in output:\n"
        + "\n".join(f"  - {m}" for m in missing[:20])
        + ("\n  ..." if len(missing) > 20 else "")
    )


def test_missing_keyword_is_detected():
    """Fields without Field(title=...) are excluded from the keyword tree."""

    class ChildModel(BaseModel):
        documented: str = Field(..., title="DOCUMENTED", description="This has a title")
        undocumented: str  # no Field, no title

    class FakeRoot(BaseModel):
        section: list[ChildModel] = Field(..., title="SECTION", description="A section")

    root = KeywordTreeBuilder().build(FakeRoot)
    keywords = {node.keyword for node in root.walk()}

    assert "DOCUMENTED" in keywords, "Field with title= should appear in tree"
    assert "UNDOCUMENTED" not in keywords, "Field without title= should NOT appear in tree"


def test_leaf_sections_have_a_description(page):
    """Sections without child items must have a description."""
    for section in page.sections:
        if not section.items:
            assert section.description, f"Leaf section '{section.keyword}' has no items and no description"
