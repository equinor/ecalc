"""
Generate minimal YAML examples from the document model.

Produces representative snippets showing keyword structure
with placeholder values like <name>, <type>, etc.
"""

from __future__ import annotations

from scripts.yaml_reference_docs.doc_model import SectionDoc, ItemDoc


class YamlExampleBuilder:
    """Builds YAML example strings from the document model."""

    def build(self, section: SectionDoc) -> str:
        lines: list[str] = []

        if self._is_list_type(section.type_label):
            lines.append(f"{section.keyword}:")
            self._emit_list_entry(section.items, lines, indent=2)
        elif self._is_dict_type(section.type_label):
            lines.append(f"{section.keyword}:")
            lines.append(f"  <name>:")
            self._emit_mapping(section.items, lines, indent=4)
        elif section.items:
            lines.append(f"{section.keyword}:")
            self._emit_mapping(section.items, lines, indent=2)
        else:
            lines.append(f"{section.keyword}: {self._placeholder(section.type_label, section.keyword)}")

        return "\n".join(lines)

    def build_item(self, item: ItemDoc) -> str:
        """Build a YAML example for a variant block.

        Renders the variant's children as peer-level fields (not nested),
        since variants represent TYPE values, not YAML keywords.
        """
        real_children = [c for c in item.children if not c.is_variant]

        if not real_children:
            return ""

        lines: list[str] = []
        for child in real_children:
            self._emit_item(child, lines, "", 0)

        return "\n".join(lines)

    # ── Tree walkers ──────────────────────────────────────────────────

    def _emit_list_entry(self, items: list[ItemDoc], lines: list[str], indent: int) -> None:
        pad = " " * indent
        first = True
        for item in items:
            if item.is_variant:
                continue
            prefix = f"{pad}- " if first else f"{pad}  "
            first = False
            self._emit_item(item, lines, prefix, indent + 2)

    def _emit_mapping(self, items: list[ItemDoc], lines: list[str], indent: int) -> None:
        pad = " " * indent
        for item in items:
            if item.is_variant:
                continue
            self._emit_item(item, lines, pad, indent)

    def _emit_item(self, item: ItemDoc, lines: list[str], prefix: str, indent: int) -> None:
        real_children = [c for c in item.children if not c.is_variant]

        if real_children:
            if self._is_list_type(item.type_label):
                lines.append(f"{prefix}{item.keyword}:")
                self._emit_list_entry(real_children, lines, indent + 2)
            elif self._is_dict_type(item.type_label):
                lines.append(f"{prefix}{item.keyword}:")
                lines.append(f"{' ' * (indent + 2)}<name>:")
                self._emit_mapping(real_children, lines, indent + 4)
            else:
                lines.append(f"{prefix}{item.keyword}:")
                self._emit_mapping(real_children, lines, indent + 2)
        else:
            lines.append(f"{prefix}{item.keyword}: {self._value(item)}")

    # ── Value resolution ──────────────────────────────────────────────

    def _value(self, item: ItemDoc) -> str:
        """Just a clean placeholder — no comments."""
        return self._placeholder(item.type_label, item.keyword)

    @staticmethod
    def _placeholder(type_label: str, keyword: str = "") -> str:
        tag = f"<{keyword.lower()}>" if keyword else "<value>"
        if not type_label:
            return tag

        tl = type_label.strip()

        # Compound types — always use placeholder
        if "∣" in tl or "Union" in tl:
            return tag

        # List/dict wrappers — always use placeholder
        if tl.startswith("list[") or tl.startswith("dict["):
            return tag

        # Simple scalar types
        if tl in ("text", "str"):
            return tag
        if tl in ("number", "float"):
            return tag
        if tl in ("integer", "int"):
            return tag
        if tl in ("true / false", "bool"):
            return tag
        if tl == "datetime":
            return "YYYY-MM-DD"

        # Single-value enum: "SRK | PR | GERG_SRK" — still use placeholder
        if "|" in tl:
            return tag

        # Named model type like "Composition", "Rate" — use placeholder
        return tag

    @staticmethod
    def _is_list_type(type_label: str) -> bool:
        return type_label.startswith("list[") if type_label else False

    @staticmethod
    def _is_dict_type(type_label: str) -> bool:
        return type_label.startswith("dict[") if type_label else False
