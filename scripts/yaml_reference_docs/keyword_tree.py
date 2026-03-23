"""
Build a keyword tree from the eCalc Pydantic model graph.

Walks from a root model (YamlAsset) and produces KeywordNode objects
representing each YAML keyword in its hierarchical context.
TYPE-discriminated unions are split into variant branches.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import get_origin, Literal, Annotated, get_args
from collections.abc import Iterator

from pydantic import BaseModel
from pydantic.fields import FieldInfo

from .introspect import field_type_label, format_default, extract_child_models
from .mdx import is_yaml_keyword


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class KeywordNode:
    """
    One YAML keyword in its hierarchical context.

    A node like NAME under INSTALLATIONS → FUEL_CONSUMERS has
    path=("INSTALLATIONS", "FUEL_CONSUMERS", "NAME") and depth=3.
    """

    keyword: str
    path: tuple[str, ...]
    description: str
    type_label: str
    required: bool
    default: str
    children: list[KeywordNode] = field(default_factory=list)
    field_info: FieldInfo | None = None
    source_model: type[BaseModel] | None = None
    variants: list[type[BaseModel]] = field(default_factory=list)

    @property
    def depth(self) -> int:
        return len(self.path)

    @property
    def is_leaf(self) -> bool:
        return len(self.children) == 0

    def walk(self) -> Iterator[KeywordNode]:
        """Depth-first traversal of this node and all descendants."""
        yield self
        for child in self.children:
            yield from child.walk()

    def keywords_flat(self) -> dict[str, list[KeywordNode]]:
        """Group all nodes by keyword name (flat catalogue view)."""
        result: dict[str, list[KeywordNode]] = {}
        for node in self.walk():
            if node.keyword == "ROOT":
                continue
            result.setdefault(node.keyword, []).append(node)
        return result


# ---------------------------------------------------------------------------
# Tree builder
# ---------------------------------------------------------------------------


@dataclass
class KeywordTreeBuilder:
    """
    Build a KeywordNode tree by walking the Pydantic model hierarchy.

    Inspects each model's fields, extracts YAML keywords from field titles,
    and recurses into child models. When a Union type has a discriminator
    field (e.g. TYPE with Literal values), the models are grouped into
    variant branches.
    """

    group_by_type: bool = True
    deduplicate: bool = True

    def build(
        self,
        root_model: type[BaseModel],
        exclude_top_level: set[str] | None = None,
    ) -> KeywordNode:
        """Build a complete keyword tree from a root Pydantic model."""
        children = self._build_tree(root_model, path=(), seen=set())

        if exclude_top_level:
            children = [c for c in children if c.keyword not in exclude_top_level]

        return KeywordNode(
            keyword="ROOT",
            path=(),
            description="eCalc YAML configuration",
            type_label="",
            required=True,
            default="—",
            children=children,
            source_model=root_model,
        )

    def _build_tree(
        self,
        model: type[BaseModel],
        path: tuple[str, ...],
        seen: set[str],
    ) -> list[KeywordNode]:
        """
        Extract keyword nodes from a single Pydantic model's fields.

        Skips already-visited models (via `seen`) to avoid infinite recursion
        in circular model references.
        """
        model_key = f"{model.__qualname__}@{'/'.join(path)}"
        if model_key in seen:
            return []
        seen.add(model_key)

        nodes: list[KeywordNode] = []

        for field_name, fi in model.model_fields.items():
            keyword = (fi.title or "").strip()
            if not keyword or not is_yaml_keyword(keyword):
                continue

            node_path = path + (keyword,)
            child_models = extract_child_models(fi.annotation)
            children = self._build_children(child_models, node_path, seen)

            nodes.append(
                KeywordNode(
                    keyword=keyword,
                    path=node_path,
                    description=(fi.description or "").strip(),
                    type_label=field_type_label(fi),
                    required=fi.is_required(),
                    default=format_default(fi),
                    children=children,
                    field_info=fi,
                    source_model=model,
                    variants=child_models,
                )
            )

        return self._maybe_deduplicate(nodes)

    def _build_children(
        self,
        child_models: list[type[BaseModel]],
        node_path: tuple[str, ...],
        seen: set[str],
    ) -> list[KeywordNode]:
        """
        Recurse into child models to build their keyword nodes.

        If the children form a discriminated union (e.g. multiple models
        with different TYPE values), splits them into variant branches.
        Otherwise, flattens all child fields into a single list.
        """
        if self.group_by_type:
            disc_field, typed, untyped = self._split_by_discriminator(child_models)
            if len(typed) > 1:
                return self._build_typed_children(typed, untyped, node_path, seen)

        children: list[KeywordNode] = []
        for child in child_models:
            children.extend(self._build_tree(child, node_path, seen))
        return self._maybe_deduplicate(children)

    def _build_typed_children(
        self,
        typed_variants: list[tuple[str, list[type[BaseModel]]]],
        untyped_variants: list[type[BaseModel]],
        node_path: tuple[str, ...],
        seen: set[str],
    ) -> list[KeywordNode]:
        """
        Build keyword nodes for a discriminated union (e.g. TYPE = DEFAULT | MISCELLANEOUS).

        Fields shared across all variants (like NAME) are emitted once.
        Each discriminator value (e.g. DEFAULT) becomes a variant node
        containing only its unique fields.
        """
        children: list[KeywordNode] = []

        all_field_sets = [set(m.model_fields.keys()) for _, models in typed_variants for m in models]
        shared_fields = set.intersection(*all_field_sets) if all_field_sets else set()

        # Build TYPE node manually with all discriminator values
        all_type_values = [tv for tv, _ in typed_variants]
        type_node = KeywordNode(
            keyword="TYPE",
            path=node_path + ("TYPE",),
            description="The type of the component",
            type_label=", ".join(all_type_values),
            required=True,
            default="—",
            children=[],
            field_info=None,
            source_model=None,
        )
        children.append(type_node)
        shared_emitted: set[str] = {"TYPE"}

        # Emit remaining shared fields from first model of first variant
        _, first_models = typed_variants[0]
        for node in self._build_tree(first_models[0], node_path, set(seen)):
            if node.keyword == "TYPE":
                continue
            if node.keyword == "NAME" or node.keyword.lower() in shared_fields:
                children.append(node)
                shared_emitted.add(node.keyword)

        for type_val, models in typed_variants:
            variant_path = node_path + (type_val,)

            if len(models) > 1:
                nested_disc, nested_typed = self._split_group_by_nested_discriminator(models, variant_path)
                if nested_disc is not None:
                    variant_children = self._build_typed_children(
                        typed_variants=nested_typed,
                        untyped_variants=[],
                        node_path=variant_path,
                        seen=set(seen),
                    )
                else:
                    variant_children = []
                    for model in models:
                        for node in self._build_tree(model, variant_path, set(seen)):
                            if node.keyword not in shared_emitted:
                                variant_children.append(node)
            else:
                variant_children = []
                for node in self._build_tree(models[0], variant_path, set(seen)):
                    if node.keyword not in shared_emitted:
                        variant_children.append(node)

            best_model = max(models, key=lambda m: len(dict(m.model_fields.items())))

            children.append(
                KeywordNode(
                    keyword=type_val,
                    path=variant_path,
                    description=f"When TYPE is {type_val}",
                    type_label="",
                    required=False,
                    default="—",
                    children=self._maybe_deduplicate(variant_children),
                    field_info=None,
                    source_model=best_model,
                    variants=models,
                )
            )

        for model in untyped_variants:
            children.extend(self._build_tree(model, node_path, set(seen)))

        return self._maybe_deduplicate(children)

    def _maybe_deduplicate(self, nodes: list[KeywordNode]) -> list[KeywordNode]:
        """Remove duplicate keyword nodes, merging their children and variants."""
        if not self.deduplicate:
            return nodes
        return _deduplicate_nodes(nodes)

    @staticmethod
    def _find_discriminator_field(child_models: list[type[BaseModel]]) -> str | None:
        """
        Find the field used as discriminator across a set of models.

        A discriminator field has a single Literal value that differs per model,
        e.g. type: Literal["PREDEFINED"] vs type: Literal["COMPOSITION"].
        """
        if len(child_models) < 2:
            return None

        # Candidate fields: present in all models with single-Literal annotation
        first_fields = dict(child_models[0].model_fields.items())  # type: ignore[misc]
        candidates: dict[str, list[str]] = {}  # field_name → [literal_values]
        for field_name in first_fields:
            values = []
            for model in child_models:
                fi = dict(model.model_fields.items()).get(field_name)  # type: ignore[misc]
                if fi is None:
                    break
                ann = fi.annotation
                while get_origin(ann) is Annotated:
                    ann = get_args(ann)[0]
                if get_origin(ann) is not Literal:
                    break
                args = get_args(ann)
                if len(args) != 1:
                    break
                v = args[0]
                values.append(v.value if isinstance(v, Enum) else str(v))
            else:
                if len(set(values)) >= 2:
                    candidates[field_name] = values

        # Prefer "type", otherwise take the first found
        if "type" in candidates:
            return "type"
        return next(iter(candidates), None)

    @staticmethod
    def _get_discriminator_value(model: type[BaseModel], field_name: str) -> str | None:
        """Get the single Literal value for a discriminator field on a model."""
        fi = model.model_fields.get(field_name)
        if fi is None:
            return None
        ann = fi.annotation
        while get_origin(ann) is Annotated:
            ann = get_args(ann)[0]
        if get_origin(ann) is Literal:
            values = get_args(ann)
            if len(values) == 1:
                v = values[0]
                return v.value if isinstance(v, Enum) else str(v)
        return None

    def _split_by_discriminator(
        self, child_models: list[type[BaseModel]]
    ) -> tuple[str | None, list[tuple[str, list[type[BaseModel]]]], list[type[BaseModel]]]:
        """
        Group child models by their discriminator field value.

        Returns (field_name, grouped_models, ungrouped_models).
        For example, models with TYPE=DEFAULT and TYPE=MISCELLANEOUS
        become [("DEFAULT", [...]), ("MISCELLANEOUS", [...])].
        Models without a discriminator value end up in ungrouped.
        """
        disc_field = self._find_discriminator_field(child_models)
        if disc_field is None:
            return None, [], child_models

        groups: dict[str, list[type[BaseModel]]] = {}
        untyped: list[type[BaseModel]] = []
        for model in child_models:
            val = self._get_discriminator_value(model, disc_field)
            if val:
                groups.setdefault(val, []).append(model)
            else:
                untyped.append(model)

        typed: list[tuple[str, list[type[BaseModel]]]] = []
        for val, models in groups.items():
            typed.append((val, models))

        return disc_field, typed, untyped

    def _split_group_by_nested_discriminator(
        self,
        models: list[type[BaseModel]],
        node_path: tuple[str, ...],
    ) -> tuple[str | None, list[tuple[str, list[type[BaseModel]]]]]:
        """
        Split models that share a top-level discriminator by a nested one.

        Used when e.g. two models both have TYPE=COMPRESSOR_CHART but differ
        on CHART_TYPE (SINGLE_SPEED vs VARIABLE_SPEED).
        """
        disc_field = self._find_discriminator_field(models)
        if disc_field is None:
            return None, []

        groups: dict[str, list[type[BaseModel]]] = {}
        for model in models:
            val = self._get_discriminator_value(model, disc_field)
            if val:
                groups.setdefault(val, []).append(model)

        if len(groups) <= 1:
            # All models have the same value — not a real nested discriminator
            return None, []

        return disc_field, [(val, group) for val, group in groups.items()]


# ---------------------------------------------------------------------------
# Debug helper
# ---------------------------------------------------------------------------


def print_tree(node: KeywordNode, indent: int = 0) -> None:
    """Print keyword tree to stdout (for debugging)."""
    prefix = "  " * indent
    req = " (required)" if node.required and node.keyword != "ROOT" else ""
    print(f"{prefix}{node.keyword}{req}")
    for child in node.children:
        print_tree(child, indent + 1)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _deduplicate_nodes(nodes: list[KeywordNode]) -> list[KeywordNode]:
    """Merge nodes with the same keyword, keeping the richest version."""
    seen: dict[str, KeywordNode] = {}
    order: list[str] = []

    for node in nodes:
        if node.keyword not in seen:
            seen[node.keyword] = node
            order.append(node.keyword)
        else:
            existing = seen[node.keyword]
            merged_children = _deduplicate_nodes(existing.children + node.children)
            merged_variants = list({id(v): v for v in existing.variants + node.variants}.values())

            seen[node.keyword] = KeywordNode(
                keyword=node.keyword,
                path=existing.path,
                description=existing.description or node.description,
                type_label=existing.type_label or node.type_label,
                required=existing.required or node.required,
                default=existing.default,
                children=merged_children,
                field_info=existing.field_info,
                source_model=existing.source_model,
                variants=merged_variants,
            )

    return [seen[k] for k in order]
