"""
Render a YAML reference Markdown page from the document model.
"""

from __future__ import annotations

import re
from datetime import date

from .doc_model import PageDoc, SectionDoc, ItemDoc
from .mdx import mdx_escape, mdx_code
from .page_builder import PageBuilder
from .keyword_tree import KeywordNode
from .example_builder import YamlExampleBuilder


_KEYWORD_URL_RE = re.compile(r"\$ECALC_DOCS_KEYWORDS_URL/\S*")
HEADING_MAX_DEPTH = 2


class MarkdownRenderer:
    """Convert a PageDoc into a Markdown string for Docusaurus."""

    def __init__(self):
        self._example_builder = YamlExampleBuilder()

    def render_page(self, page: PageDoc) -> str:
        """Render the full page with frontmatter, headings, and sections."""
        today = date.today().isoformat()
        lines = [
            "---",
            f"title: {page.title}",
            "sidebar_position: 1001",
            "toc_max_heading_level: 5",
            "---",
            "",
            f"# {page.title}",
            "",
            ":::info",
            f"This page is auto-generated from the eCalc Pydantic model. Last generated: {today}.",
            ":::",
            "",
            '<div className="yaml-reference">',
            "",
        ]
        for i, section in enumerate(page.sections):
            if i > 0:
                lines.append("---")
                lines.append("")
            lines.extend(self._render_section(section))
        lines.append("</div>")
        return "\n".join(lines)

    def _render_section(self, section: SectionDoc) -> list[str]:
        """Render a top-level section with heading, description, and YAML example."""
        lines: list[str] = []

        level = min(section.depth + 1, 6)
        hashes = "#" * max(level, 2)

        req = " *(required)*" if section.required else ""
        lines.append(f"{hashes} {section.keyword}{req} {{#{section.anchor}}}")
        lines.append("")

        # Skip type_label if it contains Python class names (Union types)
        meta_parts: list[str] = []
        if section.type_label and not _is_internal_type(section.type_label):
            meta_parts.append(mdx_code(section.type_label))
        if meta_parts:
            lines.append(" &mdash; ".join(meta_parts))
            lines.append("")

        if section.description:
            lines.append(mdx_escape(_clean_description(section.description)))
            lines.append("")

        example = self._example_builder.build(section)
        if example:
            lines.append("```yaml")
            lines.append(example.rstrip())
            lines.append("```")
            lines.append("")

        for item in section.items:
            lines.extend(self._render_item(item, indent=0, as_heading=item.depth <= HEADING_MAX_DEPTH))

        return lines

    def _render_item(self, item: ItemDoc, indent: int, as_heading: bool) -> list[str]:
        """Dispatch to heading, variant block, or bullet rendering."""
        if as_heading:
            return self._render_item_as_heading(item)
        if item.is_variant:
            return self._render_variant_block(item, indent)
        return self._render_item_as_bullet(item, indent)

    def _render_item_as_heading(self, item: ItemDoc) -> list[str]:
        """Render a keyword as a Markdown heading (used for depth ≤ HEADING_MAX_DEPTH)."""
        level = min(item.depth + 1, 6)
        hashes = "#" * max(level, 2)

        req = " *(required)*" if item.required else ""
        lines = [f"{hashes} {item.keyword}{req} {{#{item.anchor}}}"]
        lines.append("")

        variant_children = [c for c in item.children if c.is_variant]
        non_variant_children = [c for c in item.children if not c.is_variant]

        # Build type annotation
        type_str = ""
        if variant_children:
            allowed = " &#124; ".join(f"`{v.keyword}`" for v in variant_children)
            type_str = f"Allowed values: {allowed}"
        elif item.type_label and not _is_internal_type(item.type_label):
            type_str = mdx_code(item.type_label)

        default_str = ""
        if item.default and item.default != "—":
            default_str = f"default: {mdx_code(item.default)}"

        # Description with inline type when there's no default and no variants
        if item.description and type_str and not default_str and not variant_children:
            lines.append(f"{mdx_escape(_clean_description(item.description))} ({type_str})")
            lines.append("")
        else:
            if item.description:
                lines.append(mdx_escape(_clean_description(item.description)))
                lines.append("")
            meta_parts = [p for p in [type_str, default_str] if p]
            if meta_parts:
                lines.append(" · ".join(meta_parts))
                lines.append("")

        for child in non_variant_children:
            lines.extend(self._render_item(child, 0, as_heading=False))

        for child in variant_children:
            lines.extend(self._render_variant_block(child, 0))

        return lines

    def _render_variant_block(self, item: ItemDoc, indent: int) -> list[str]:
        """Render a variant as a styled <div> block (or nested bullet if indented)."""
        if indent > 0:
            return self._render_nested_variant(item, indent)

        level = min(item.depth + 2, 6)
        hashes = "#" * level

        lines = [
            f'<div className="yaml-variant">',
            "",
            f"{hashes} {mdx_escape(item.keyword)} {{#{item.anchor}}}",
            "",
        ]

        if item.description and not item.description.startswith("When "):
            lines.append(f"*{mdx_escape(_clean_description(item.description))}*")
            lines.append("")

        # YAML example for this variant
        example = self._example_builder.build_item(item)
        if example:
            lines.append("```yaml")
            lines.append(example.rstrip())
            lines.append("```")
            lines.append("")

        sub_variants = [c for c in item.children if c.is_variant]
        regular = [c for c in item.children if not c.is_variant]

        # Render additional fields as peer-level items (not nested)
        for child in regular:
            lines.extend(self._render_item(child, 0, as_heading=False))

        for sv in sub_variants:
            lines.extend(self._render_nested_variant(sv, 0))

        lines.append("</div>")
        lines.append("")

        return lines

    def _render_nested_variant(self, item: ItemDoc, indent: int) -> list[str]:
        """Render a variant inside a bullet list (for deeply nested discriminators)."""
        pad = "  " * indent

        line = f'{pad}- **{mdx_escape(item.keyword)}**<span id="{item.anchor}"></span>'
        if item.description:
            line += f"<br/>{pad}  *{mdx_escape(_clean_description(item.description))}*"

        lines = [line]

        if not item.children:
            lines.append("")

        for child in item.children:
            lines.extend(self._render_item(child, indent + 1, as_heading=False))

        if item.children:
            lines.append("")

        return lines

    def _render_item_as_bullet(self, item: ItemDoc, indent: int) -> list[str]:
        """Render a keyword as a bullet point with type, default, and description."""
        pad = "  " * indent

        req = " *(required)*" if item.required else ""
        label = f"**{mdx_escape(item.keyword)}**{req}"

        variant_children = [c for c in item.children if c.is_variant]
        non_variant_children = [c for c in item.children if not c.is_variant]

        # Determine if this field has variants (discriminator) — if so, skip type_label
        # and show variant keywords as allowed values instead
        is_enum = False
        effective_type_label = item.type_label
        if variant_children:
            # This is a discriminator field: use variant keywords as the allowed values
            effective_type_label = ""  # suppress the raw type_label (often Python class names)
            is_enum = False
        elif item.type_label and ("|" in item.type_label or "∣" in item.type_label):
            is_enum = True
            # Check if type_label contains internal Python class names
            if _is_internal_type(item.type_label):
                effective_type_label = ""
                is_enum = False

        # Build type+default string
        meta_parts: list[str] = []
        if effective_type_label and not is_enum and not _is_internal_type(effective_type_label):
            meta_parts.append(mdx_code(effective_type_label))
        if item.default and item.default != "—" and not is_enum:
            meta_parts.append(f"default: {mdx_code(item.default)}")
        meta_str = " · ".join(meta_parts)

        line = f'{pad}- {label}<span id="{item.anchor}"></span>'

        if item.description and is_enum:
            line += f"<br/>{pad}  {mdx_escape(_clean_description(item.description))}"
            line += f"<br/>{pad}  Allowed values: {mdx_code(effective_type_label)}"
            if item.default and item.default != "—":
                line += f" · default: {mdx_code(item.default)}"
        elif item.description and meta_str:
            line += f"<br/>{pad}  {mdx_escape(_clean_description(item.description))} ({meta_str})"
        elif item.description:
            line += f"<br/>{pad}  {mdx_escape(_clean_description(item.description))}"
        elif meta_str:
            line = f'{pad}- {label}: {meta_str}<span id="{item.anchor}"></span>'

        has_children = bool(non_variant_children or variant_children)

        lines = [line]
        if not has_children:
            lines.append("")

        for child in non_variant_children:
            lines.extend(self._render_item(child, indent + 1, as_heading=False))

        for child in variant_children:
            lines.extend(self._render_item(child, indent + 1, as_heading=False))

        if has_children:
            lines.append("")

        return lines


# ═════════════════════════════════════════════════════════════��═════════════
# Public API
# ═══════════════════════════════════════════════════════════════════════════


def render_full_page(root: KeywordNode) -> str:
    """Render a keyword as a bullet point with type, default, and description."""
    page = PageBuilder().build(root)
    return MarkdownRenderer().render_page(page)


# ═══════════════════════════════════════════════════════════════════════════
# Internal helpers
# ═══════════════════════════════════════════════════════════════════════════


def _is_internal_type(label: str) -> bool:
    """Return True if the type label contains Python class names users shouldn't see."""
    # Heuristic: if it contains CamelCase class names, it's internal
    import re

    return bool(re.search(r"[A-Z][a-z]+[A-Z]", label))


def _clean_description(desc: str) -> str:
    """Remove unresolved $ECALC_DOCS_KEYWORDS_URL references and trailing 'For more details, see:'."""
    desc = _KEYWORD_URL_RE.sub("", desc)
    desc = re.sub(r"\n*For more details, see:\s*", "", desc)
    return desc.strip()
