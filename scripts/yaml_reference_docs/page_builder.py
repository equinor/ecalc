import re

from scripts.yaml_reference_docs.doc_model import ItemDoc, SectionDoc, PageDoc
from scripts.yaml_reference_docs.mdx import clean_description
from scripts.yaml_reference_docs.keyword_tree import KeywordNode


class PageBuilder:
    """
    Convert a KeywordNode tree into a PageDoc for rendering.

    Sections are top-level keywords (TIME_SERIES, INSTALLATIONS).
    Items are nested keywords (NAME, FILE, TYPE).
    Variants are TYPE-discriminated branches (DEFAULT, MISCELLANEOUS).
    """

    def build(self, root: KeywordNode) -> PageDoc:
        page = PageDoc(title="YAML Overview")
        for child in root.children:
            section = self._build_section(child)
            if section is not None:
                page.sections.append(section)
        return page

    def _build_section(self, node: KeywordNode) -> SectionDoc | None:
        """
        Build a top-level section (e.g. TIME_SERIES, FUEL_TYPES).

        Returns None for empty sections with no description.
        """
        real_children = [c for c in node.children if not _is_variant(c)]
        variant_children = [c for c in node.children if _is_variant(c)]

        items = self._build_items_with_variants(real_children, variant_children)

        # Keep sections that have items OR a description (leaf keywords like START, END)
        if not items and not clean_description(node.description):
            return None

        return SectionDoc(
            keyword=node.keyword,
            anchor=_anchor(node),
            depth=node.depth,
            description=clean_description(node.description),
            type_label=node.type_label or "",
            required=node.required,
            items=items,
        )

    def _build_items_with_variants(
        self, real_children: list[KeywordNode], variant_children: list[KeywordNode]
    ) -> list[ItemDoc]:
        """
        Build items, attaching variant blocks to their discriminator field.

        If variants exist (e.g. DEFAULT, MISCELLANEOUS), finds the discriminator
        field (usually TYPE) and nests the variant items as its children.
        This way the renderer can show variant blocks under the correct field.

        The discriminator is identified by matching variant keywords against
        field type_labels, then variant descriptions, then common names (TYPE, CHART_TYPE).
        """
        if not variant_children:
            return [self._build_item(c) for c in real_children]

        variant_items = [self._build_variant_item(v) for v in variant_children]

        # Find discriminator keyword from variant descriptions
        # e.g. "When TYPE is PREDEFINED" → "TYPE"
        disc_keyword_from_desc = None
        for v in variant_children:
            if v.description and v.description.startswith("When "):
                parts = v.description.split(" is ", 1)
                if len(parts) == 2:
                    candidate = parts[0].replace("When ", "").strip()
                    if any(c.keyword == candidate for c in real_children):
                        disc_keyword_from_desc = candidate
                        break

        # Strategy: if description says "TYPE" but a more specific field exists
        # whose type_label is a Literal matching variant keywords, prefer that field.
        # e.g. FLUID_MODEL_TYPE has type_label "PREDEFINED" which matches variant "PREDEFINED"
        variant_keywords = {v.keyword for v in variant_children}

        disc_keyword = None

        # First: find field whose type_label exactly matches one of the variant keywords
        # (indicates it's a Literal discriminator like FLUID_MODEL_TYPE: Literal["PREDEFINED"])
        for c in real_children:
            if c.type_label and c.type_label in variant_keywords:
                disc_keyword = c.keyword
                break

        # If no exact match, try field whose type_label contains a variant keyword
        if disc_keyword is None:
            for c in real_children:
                if c.type_label and any(vk in c.type_label for vk in variant_keywords):
                    # But don't pick a field that has ALL variant keywords (that's the enum itself)
                    disc_keyword = c.keyword
                    break

        # Fall back to description-based match
        if disc_keyword is None:
            disc_keyword = disc_keyword_from_desc

        # Last resort fallback
        if disc_keyword is None:
            for c in real_children:
                if c.keyword in ("TYPE", "CHART_TYPE"):
                    disc_keyword = c.keyword
                    break
            else:
                disc_keyword = "TYPE"

        items: list[ItemDoc] = []
        attached = False
        for c in real_children:
            item = self._build_item(c)
            if c.keyword == disc_keyword and not attached:
                item.children.extend(variant_items)
                attached = True
            items.append(item)

        if not attached:
            items.extend(variant_items)

        return items

    def _build_item(self, node: KeywordNode) -> ItemDoc:
        """Build a regular keyword item (e.g. NAME, FILE, EXTRAPOLATION)."""
        real_children = [c for c in node.children if not _is_variant(c)]
        variant_children = [c for c in node.children if _is_variant(c)]

        children = self._build_items_with_variants(real_children, variant_children)

        return ItemDoc(
            keyword=node.keyword,
            required=node.required,
            type_label=node.type_label or "",
            default=node.default or "",
            description=clean_description(node.description),
            anchor=_anchor(node),
            depth=node.depth,
            children=children,
        )

    def _build_variant_item(self, vnode: KeywordNode) -> ItemDoc:
        """
        Build a variant block item (e.g. DEFAULT, MISCELLANEOUS, PREDEFINED).

        Variants represent one possible value of a discriminator field.
        Their description comes from the Pydantic model's docstring.
        """
        real_children = [c for c in vnode.children if not _is_variant(c)]
        variant_children = [c for c in vnode.children if _is_variant(c)]

        children = self._build_items_with_variants(real_children, variant_children)

        desc = ""
        if vnode.source_model and vnode.source_model.__doc__:
            desc = clean_description(vnode.source_model.__doc__)

        return ItemDoc(
            keyword=vnode.keyword,
            required=False,
            type_label="",
            default="",
            description=desc,
            anchor=_anchor(vnode),
            depth=vnode.depth,
            is_variant=True,
            children=children,
        )


# ═══════════════════════════════════════════════════════════════════════════
# Internal helpers
# ═══════════════════════════════════════════════════════════════════════════


def _is_variant(node: KeywordNode) -> bool:
    """Check if a node represents a TYPE variant (e.g. "When TYPE is DEFAULT")."""
    if not node.description:
        return False
    return bool(re.match(r"When \w+ is ", node.description))


def _anchor(node: KeywordNode) -> str:
    """Generate an HTML anchor from the node path (e.g. "time_series-type-default")."""
    return "-".join(node.path).lower()
