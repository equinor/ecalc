"""
Generate process reference documentation from pydantic models.

Two-step process:
1. Build a tree of DocNode objects by introspecting the YamlAsset pydantic model.
2. Render that tree into a single-page Docusaurus markdown document.

Usage:
    uv run python src/generate_yaml_asset_docs.py
"""

from __future__ import annotations

import inspect
import re
import types
from collections.abc import Callable
from pathlib import Path
from typing import Annotated, Any, Literal, Union, get_args, get_origin

import yaml
from pydantic import BaseModel
from pydantic.fields import FieldInfo
from pydantic_core import PydanticUndefined

from libecalc.presentation.yaml.yaml_types.components.yaml_asset import YamlAsset, YamlDefinitions
from libecalc.presentation.yaml.yaml_types.process.yaml_process_references import DefinitionReference
from libecalc.testing.process_builders import (
    YamlCommonStreamDistributionBuilder,
    YamlCompositionFluidDefinitionBuilder,
    YamlCompressorBuilder,
    YamlCompressorChartBuilder,
    YamlCompressorModelChartBuilder,
    YamlCurveBuilder,
    YamlIndividualStreamDistributionBuilder,
    YamlInletStreamBuilder,
    YamlInletStreamRateBuilder,
    YamlLiquidRemoverBuilder,
    YamlMixerBuilder,
    YamlPredefinedFluidDefinitionBuilder,
    YamlPressureDropperBuilder,
    YamlProcessPipelineBuilder,
    YamlProcessSimulationBuilder,
    YamlSplitterBuilder,
    YamlTemperatureSetterBuilder,
)

# Top-level YamlAsset fields to document (by python attribute name)
INCLUDE_FIELDS = {"definitions", "process_pipelines", "inlet_streams", "process_simulations"}

# Maximum recursion depth to prevent infinite loops on circular references
MAX_DEPTH = 8


class Example:
    """
    An example YAML snippet associated with a path in the documentation tree.

    Attributes:
        path: Dot-separated YAML key path (e.g. "DEFINITIONS.PROCESS_UNITS.COMPRESSOR").
              For discriminated union variants, the variant name is used as the last segment.
        builder: A callable that returns a validated pydantic model instance.
    """

    def __init__(self, path: str, builder: Callable):
        self.path = path
        self.builder = builder

    @property
    def model(self) -> BaseModel:
        return self.builder()

    @property
    def yaml_str(self) -> str:
        return _model_to_yaml(self.model)


def _model_to_yaml(model: BaseModel) -> str:
    """Serialize a pydantic model to a YAML string."""
    data = model.model_dump(serialize_as_any=True, mode="json", exclude_unset=True, by_alias=True)
    return yaml.dump(data, default_flow_style=False, sort_keys=False).rstrip()


def _model_to_yaml_with_ellipsis(model: BaseModel, child_paths: set[str], current_path: str) -> str:
    """
    Serialize a pydantic model to YAML, replacing fields that have their own
    registered examples with '...' ellipsis.

    Args:
        model: The pydantic model to serialize.
        child_paths: Set of all registered example paths.
        current_path: The path of the current model in the tree.
    """
    data = model.model_dump(serialize_as_any=True, mode="json", exclude_unset=True, by_alias=True)
    data = _replace_with_ellipsis(data, child_paths, current_path)
    output = yaml.dump(data, default_flow_style=False, sort_keys=False).rstrip()
    # Remove YAML quoting around ellipsis — '...' -> ...
    output = output.replace("'...'", "...")
    return output


def _replace_with_ellipsis(data: dict | list | Any, child_paths: set[str], current_path: str) -> Any:
    """Recursively replace dict values whose path matches a child example with '...'."""
    if isinstance(data, dict):
        result = {}
        for key, value in data.items():
            field_path = f"{current_path}.{key}"
            # Check if this field or any variant of it has a registered example
            if any(p == field_path or p.startswith(field_path + ".") for p in child_paths):
                result[key] = "..."
            elif isinstance(value, (dict, list)):
                result[key] = _replace_with_ellipsis(value, child_paths, field_path)
            else:
                result[key] = value
        return result
    elif isinstance(data, list):
        return [_replace_with_ellipsis(item, child_paths, current_path) for item in data]
    return data


# ---------------------------------------------------------------------------
# Example registry
#
# Each Example maps a YAML key path to a builder.
# To fine-tune the docs, remove entries from this list — the field will then
# render without a dedicated code block (and parents won't use ellipsis for it).
# ---------------------------------------------------------------------------

EXAMPLES: list[Example] = [
    # --- DEFINITIONS.PROCESS_UNITS variants ---
    Example(
        "DEFINITIONS.PROCESS_UNITS.COMPRESSOR",
        lambda: YamlCompressorBuilder().with_test_data().validate(),
    ),
    Example(
        "DEFINITIONS.PROCESS_UNITS.COMPRESSOR.COMPRESSOR_MODEL",
        lambda: YamlCompressorModelChartBuilder().with_test_data().validate(),
    ),
    Example(
        "DEFINITIONS.PROCESS_UNITS.COMPRESSOR.COMPRESSOR_MODEL.CHART",
        lambda: YamlCompressorChartBuilder().with_test_data().validate(),
    ),
    Example(
        "DEFINITIONS.PROCESS_UNITS.COMPRESSOR.COMPRESSOR_MODEL.CHART.CURVES.YAMLCURVE",
        lambda: YamlCurveBuilder().with_test_data().validate(),
    ),
    Example(
        "DEFINITIONS.PROCESS_UNITS.PRESSURE_DROPPER",
        lambda: YamlPressureDropperBuilder().with_test_data().validate(),
    ),
    Example(
        "DEFINITIONS.PROCESS_UNITS.TEMPERATURE_SETTER",
        lambda: YamlTemperatureSetterBuilder().with_test_data().validate(),
    ),
    Example(
        "DEFINITIONS.PROCESS_UNITS.LIQUID_REMOVER",
        lambda: YamlLiquidRemoverBuilder().with_test_data().validate(),
    ),
    Example(
        "DEFINITIONS.PROCESS_UNITS.MIXER",
        lambda: YamlMixerBuilder().with_test_data().validate(),
    ),
    Example(
        "DEFINITIONS.PROCESS_UNITS.SPLITTER",
        lambda: YamlSplitterBuilder().with_test_data().validate(),
    ),
    # --- DEFINITIONS.FLUIDS variants ---
    Example(
        "DEFINITIONS.FLUIDS.PREDEFINED",
        lambda: YamlPredefinedFluidDefinitionBuilder().with_test_data().validate(),
    ),
    Example(
        "DEFINITIONS.FLUIDS.COMPOSITION",
        lambda: YamlCompositionFluidDefinitionBuilder().with_test_data().validate(),
    ),
    # --- INLET_STREAMS ---
    Example(
        "INLET_STREAMS",
        lambda: YamlInletStreamBuilder().with_test_data().validate(),
    ),
    Example(
        "INLET_STREAMS.RATE",
        lambda: YamlInletStreamRateBuilder().with_test_data().validate(),
    ),
    # --- PROCESS_PIPELINES ---
    Example(
        "PROCESS_PIPELINES",
        lambda: YamlProcessPipelineBuilder().with_test_data().validate(),
    ),
    # --- PROCESS_SIMULATIONS ---
    Example(
        "PROCESS_SIMULATIONS",
        lambda: YamlProcessSimulationBuilder().with_test_data().validate(),
    ),
    Example(
        "PROCESS_SIMULATIONS.STREAM_DISTRIBUTION.COMMON_STREAM",
        lambda: YamlCommonStreamDistributionBuilder().with_test_data().validate(),
    ),
    Example(
        "PROCESS_SIMULATIONS.STREAM_DISTRIBUTION.INDIVIDUAL_STREAMS",
        lambda: YamlIndividualStreamDistributionBuilder().with_test_data().validate(),
    ),
]


class ExampleRegistry:
    """
    Provides lookup of examples by path, and determines which fields should
    be abbreviated with ellipsis in parent examples.
    """

    def __init__(self, examples: list[Example]):
        self._examples: dict[str, Example] = {e.path: e for e in examples}
        self._all_paths: set[str] = set(self._examples.keys())

    def get(self, path: str) -> Example | None:
        """Get an example for an exact path."""
        return self._examples.get(path)

    def has_child_examples(self, path: str) -> bool:
        """Check if any registered example is a descendant of this path."""
        prefix = path + "."
        return any(p.startswith(prefix) for p in self._all_paths)

    def child_paths_for(self, path: str) -> set[str]:
        """Get all registered paths that are descendants of the given path."""
        prefix = path + "."
        return {p for p in self._all_paths if p.startswith(prefix)}

    def render_example(self, path: str) -> str | None:
        """
        Render the YAML example for a path.
        If the example has child examples registered, those fields get '...' in the output.
        """
        example = self.get(path)
        if example is None:
            return None

        child_paths = self.child_paths_for(path)
        if child_paths:
            return _model_to_yaml_with_ellipsis(example.model, child_paths, path)
        else:
            return example.yaml_str


class DocNode:
    """
    Represents a single node in the YAML configuration documentation tree.

    Each node corresponds to a YAML key (field) in the model hierarchy.
    Keeps a reference to the original pydantic FieldInfo for maximum flexibility.
    """

    def __init__(
        self,
        name: str,
        field_info: FieldInfo | None = None,
        type_annotation: Any = None,
        children: list[DocNode] | None = None,
        parent: DocNode | None = None,
        is_discriminated_variant: bool = False,
        is_definition_reference: bool = False,
    ):
        self.name = name
        self.field_info = field_info
        self.type_annotation = type_annotation
        self.children = children or []
        self.parent = parent
        self.is_discriminated_variant = is_discriminated_variant
        self.is_definition_reference = is_definition_reference

    @property
    def title(self) -> str:
        """The YAML key title (from field_info.title, or uppercased name)."""
        if self.field_info and self.field_info.title:
            return self.field_info.title
        return self.name.upper()

    @property
    def description(self) -> str | None:
        """Human-readable description from the pydantic field."""
        if self.field_info and self.field_info.description:
            return self.field_info.description
        return None

    @property
    def is_required(self) -> bool:
        """Whether this field is required (no default value)."""
        if self.field_info is None:
            return False
        return self.field_info.is_required()

    @property
    def default(self) -> Any:
        """The default value, if any."""
        if self.field_info is None:
            return None
        d = self.field_info.default
        if d is PydanticUndefined:
            return None
        return d

    @property
    def has_default_factory(self) -> bool:
        """Whether this field uses a default_factory."""
        if self.field_info is None:
            return False
        return self.field_info.default_factory is not None

    def __repr__(self) -> str:
        return f"DocNode({self.title}, children={len(self.children)})"


def _unwrap_annotation(annotation: Any) -> Any:
    """Unwrap Annotated[X, ...] to get the inner type."""
    if get_origin(annotation) is Annotated:
        args = get_args(annotation)
        return args[0] if args else annotation
    return annotation


def _get_inner_models(annotation: Any) -> list[type[BaseModel]]:
    """
    Extract BaseModel subclass(es) from a type annotation.
    Handles: BaseModel, list[BaseModel], dict[str, BaseModel], Union[...], Annotated[...].
    """
    annotation = _unwrap_annotation(annotation)
    origin = get_origin(annotation)

    if origin is Union or origin is types.UnionType:
        args = get_args(annotation)
        models = []
        for arg in args:
            if arg is type(None):
                continue
            models.extend(_get_inner_models(arg))
        return models

    if origin is list:
        args = get_args(annotation)
        if args:
            return _get_inner_models(args[0])
        return []

    if origin is dict:
        args = get_args(annotation)
        if args and len(args) == 2:
            return _get_inner_models(args[1])
        return []

    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return [annotation]

    return []


def _is_discriminated_union(annotation: Any) -> bool:
    """Check if an annotation is a discriminated union (multiple BaseModel variants)."""
    models = _get_inner_models(annotation)
    return len(models) > 1 and all(isinstance(m, type) and issubclass(m, BaseModel) for m in models)


def _get_discriminator_value(model: type[BaseModel]) -> str | None:
    """
    Extract the discriminator value from a model's Literal type field.

    For example, if the model has `type: Literal["COMPRESSOR"]`, returns "COMPRESSOR".
    Looks for common discriminator field names: 'type', 'method'.
    """
    for field_name in ("type", "method"):
        if field_name not in model.model_fields:
            continue
        annotation = model.__annotations__.get(field_name)
        annotation = _unwrap_annotation(annotation)
        if get_origin(annotation) is Literal:
            args = get_args(annotation)
            if args:
                return str(args[0])
    return None


def build_tree(
    model: type[BaseModel],
    include_fields: set[str] | None = None,
    _depth: int = 0,
    _seen: set[type] | None = None,
) -> list[DocNode]:
    """
    Recursively build a documentation tree from a pydantic BaseModel.

    Args:
        model: The pydantic model class to introspect.
        include_fields: If provided, only include these field names (top-level filter).
        _depth: Current recursion depth (internal).
        _seen: Set of already-visited model types to prevent infinite recursion.

    Returns:
        List of DocNode representing the model's fields.
    """
    if _seen is None:
        _seen = set()

    if _depth >= MAX_DEPTH or model in _seen:
        return []

    _seen = _seen | {model}
    nodes = []

    for field_name, field_info in model.model_fields.items():
        if include_fields and field_name not in include_fields:
            continue

        annotation = model.__annotations__.get(field_name, None)
        # Fall back to field_info.annotation for generic/parameterized models
        if annotation is None and field_info.annotation is not None:
            annotation = field_info.annotation
        node = DocNode(
            name=field_name,
            field_info=field_info,
            type_annotation=annotation,
        )

        # Determine children by recursing into nested models
        # Skip recursion for fields that accept a DefinitionReference — these are
        # documented under DEFINITIONS and should just link there.
        if _has_definition_reference(annotation):
            node.is_definition_reference = True
        else:
            inner_models = _get_inner_models(annotation)

            if _is_discriminated_union(annotation):
                # Create child nodes for each variant
                for variant_model in inner_models:
                    variant_name = _get_discriminator_value(variant_model) or variant_model.__name__
                    variant_node = DocNode(
                        name=variant_name,
                        field_info=None,
                        type_annotation=variant_model,
                        parent=node,
                        is_discriminated_variant=True,
                    )
                    variant_node.children = build_tree(variant_model, _depth=_depth + 1, _seen=_seen)
                    node.children.append(variant_node)
            elif len(inner_models) == 1:
                # Single nested model — recurse directly
                node.children = build_tree(inner_models[0], _depth=_depth + 1, _seen=_seen)

        nodes.append(node)

    return nodes


def build_yaml_asset_tree() -> list[DocNode]:
    """Build the documentation tree for YamlAsset, limited to the relevant sections."""
    return build_tree(YamlAsset, include_fields=INCLUDE_FIELDS)


# --- Step 2: Render tree to markdown ---


# Maximum heading level to show in sidebar TOC, per top-level field name.
# h2=top-level, h3=one below, h4=two below. Anything deeper uses h5+ (hidden from sidebar).
SIDEBAR_DEPTH: dict[str, int] = {
    "definitions": 4,  # DEFINITIONS > PROCESS_UNITS > COMPRESSOR (h2, h3, h4)
    "inlet_streams": 2,  # INLET_STREAMS only (h2)
    "process_pipelines": 2,  # PROCESS_PIPELINES only (h2)
    "process_simulations": 2,  # PROCESS_SIMULATIONS only (h2)
}


class MarkdownBuilder:
    def __init__(self):
        self._lines: list[str] = []

    def heading(self, level: int, text: str) -> MarkdownBuilder:
        self._lines.append(f"{'#' * level} {text}")
        self._lines.append("")
        return self

    def line(self, text: str = "") -> MarkdownBuilder:
        self._lines.append(text)
        return self

    def paragraph(self, text: str) -> MarkdownBuilder:
        self._lines.append(text)
        self._lines.append("")
        return self

    def code_block(self, code: str, language: str = "yaml") -> MarkdownBuilder:
        self._lines.append(f"```{language}")
        self._lines.append(code)
        self._lines.append("```")
        self._lines.append("")
        return self

    def table(self, headers: list[str], rows: list[list[str]]) -> MarkdownBuilder:
        self._lines.append("| " + " | ".join(headers) + " |")
        self._lines.append("| " + " | ".join("---" for _ in headers) + " |")
        for row in rows:
            self._lines.append("| " + " | ".join(row) + " |")
        self._lines.append("")
        return self

    def tabs_start(self) -> MarkdownBuilder:
        self._lines.append("<Tabs>")
        return self

    def tabs_end(self) -> MarkdownBuilder:
        self._lines.append("</Tabs>")
        self._lines.append("")
        return self

    def tab_item_start(self, label: str, value: str | None = None) -> MarkdownBuilder:
        val = value or label
        self._lines.append(f'<TabItem value="{val}" label="{label}">')
        self._lines.append("")
        return self

    def tab_item_end(self) -> MarkdownBuilder:
        self._lines.append("</TabItem>")
        self._lines.append("")
        return self

    def build(self) -> str:
        return "\n".join(self._lines)


def _get_literal_values(annotation: Any) -> list[str] | None:
    """
    Extract values from a Literal type annotation.
    Returns a list of string values, or None if not a Literal.
    """
    annotation = _unwrap_annotation(annotation)
    if get_origin(annotation) is Literal:
        return [str(arg) for arg in get_args(annotation)]
    return None


def _has_definition_reference(annotation: Any) -> bool:
    """Check if a type annotation includes DefinitionReference in a union."""
    annotation = _unwrap_annotation(annotation)
    origin = get_origin(annotation)
    if origin is Union or origin is types.UnionType:
        return any(arg is DefinitionReference for arg in get_args(annotation))
    return annotation is DefinitionReference


def _build_definitions_type_map() -> dict[type, str]:
    """
    Build a mapping from BaseModel types to their DEFINITIONS subsection title.

    Introspects YamlDefinitions to find which model types belong to which
    subsection (e.g. YamlCompressorDefinition -> "PROCESS_UNITS").
    """
    type_to_section: dict[type, str] = {}

    for field_name, field_info in YamlDefinitions.model_fields.items():
        annotation = YamlDefinitions.__annotations__.get(field_name)
        if annotation is None:
            continue
        title = field_info.title or field_name.upper()
        # Extract model types from the dict value annotation
        for model_type in _get_inner_models(annotation):
            type_to_section[model_type] = title

    return type_to_section


# Pre-built at module level for use by the renderer
_DEFINITIONS_TYPE_MAP: dict[type, str] = _build_definitions_type_map()


def _resolve_definition_section(annotation: Any) -> str | None:
    """
    Given a field annotation that includes DefinitionReference, find which
    DEFINITIONS subsection it refers to by matching the companion model types.

    Returns the subsection title (e.g. "PROCESS_UNITS", "FLUIDS") or None.
    """
    annotation = _unwrap_annotation(annotation)
    origin = get_origin(annotation)

    if origin is Union or origin is types.UnionType:
        args = get_args(annotation)
    else:
        return None

    for arg in args:
        if arg is DefinitionReference:
            continue
        # Check inner models of each non-DefinitionReference arg
        for model_type in _get_inner_models(arg):
            if model_type in _DEFINITIONS_TYPE_MAP:
                return _DEFINITIONS_TYPE_MAP[model_type]

    return None


def _make_field_anchor(path: str) -> str:
    """Generate a URL-friendly anchor from a path."""
    return path.lower().replace(".", "-").replace("_", "-")


def _render_fields_table(nodes: list[DocNode], parent_path: str = "") -> list[list[str]]:
    """Build table rows for a list of child DocNodes."""
    rows = []
    for node in nodes:
        if node.is_discriminated_variant:
            continue
        desc = ""
        # For Literal types, always show the literal values as description
        if node.type_annotation:
            literal_values = _get_literal_values(node.type_annotation)
            if literal_values:
                desc = " \\| ".join(f"`{v}`" for v in literal_values)
        if not desc and node.description:
            desc = _clean_description(node.description)

        # For fields that accept a DefinitionReference, add a note about inline vs reference
        # and link to the specific DEFINITIONS subsection
        if node.type_annotation and _has_definition_reference(node.type_annotation):
            section = _resolve_definition_section(node.type_annotation)
            if section:
                # Docusaurus auto-generates heading IDs by lowercasing the heading text
                section_anchor = section.lower()
                ref_note = f"Inline definition or reference. See [DEFINITIONS.{section}](#{section_anchor})."
            else:
                ref_note = "Inline definition or reference to [DEFINITIONS](#definitions)."
            desc = f"{desc} {ref_note}" if desc else ref_note

        if node.is_required:
            status = "Required"
        elif node.default is not None:
            status = f"Default: `{node.default}`"
        else:
            status = "Optional"

        # Link to the expanded definition below if this node has children
        if node.children:
            anchor = _make_field_anchor(f"{parent_path}.{node.title}")
            key_cell = f"[`{node.title}`](#{anchor})"
        else:
            key_cell = f"`{node.title}`"

        rows.append([key_cell, desc, status])
    return rows


def _render_variants_as_tabs(
    variant_children: list[DocNode],
    md: MarkdownBuilder,
    registry: ExampleRegistry,
    parent_path: str,
    parent_title: str | None = None,
) -> None:
    """Render discriminated union variants inside Docusaurus Tabs."""
    if not variant_children:
        return

    if parent_title:
        anchor = _make_field_anchor(parent_path)
        md.line(f"##### {parent_title} {{/* #{anchor} */}}")
        md.line("")

    md.tabs_start()
    for variant in variant_children:
        variant_path = f"{parent_path}.{variant.title}"
        md.tab_item_start(label=variant.title)

        docstring = _get_model_docstring(variant.type_annotation)
        if docstring:
            md.paragraph(docstring)

        # Render example from registry
        example_yaml = registry.render_example(variant_path)
        if example_yaml:
            md.code_block(example_yaml)

        variant_non_variant = [c for c in variant.children if not c.is_discriminated_variant]
        if variant_non_variant:
            table_rows = _render_fields_table(variant_non_variant, parent_path=variant_path)
            if table_rows:
                md.table(["Key", "Description", "Status"], table_rows)
            _render_nested_fields(variant_non_variant, md, registry, variant_path)

        md.tab_item_end()
    md.tabs_end()


def _render_nested_fields(
    nodes: list[DocNode], md: MarkdownBuilder, registry: ExampleRegistry, parent_path: str
) -> None:
    """
    Recursively render nested complex fields below a table.

    For each node that has children (and is not a discriminated variant),
    render a bold label followed by its fields table, then recurse.
    """
    for node in nodes:
        if node.is_discriminated_variant:
            continue
        if not node.children:
            continue

        node_path = f"{parent_path}.{node.title}"

        # Check if this node has non-variant children to display
        non_variant_children = [c for c in node.children if not c.is_discriminated_variant]
        variant_children = [c for c in node.children if c.is_discriminated_variant]

        if non_variant_children:
            anchor = _make_field_anchor(node_path)
            md.line(f"##### {node.title} {{/* #{anchor} */}}")
            md.line("")

            if node.description:
                md.paragraph(_clean_description(node.description))

            # Render example from registry
            example_yaml = registry.render_example(node_path)
            if example_yaml:
                md.code_block(example_yaml)

            table_rows = _render_fields_table(non_variant_children, parent_path=node_path)
            if table_rows:
                md.table(["Key", "Description", "Status"], table_rows)

            # Recurse into children that themselves have children
            _render_nested_fields(non_variant_children, md, registry, node_path)

        # Render discriminated union variants with tabs
        if variant_children:
            _render_variants_as_tabs(variant_children, md, registry, node_path, parent_title=node.title)


def render_tree(
    nodes: list[DocNode],
    depth: int = 2,
    path: str = "",
    max_sidebar_depth: int = 6,
    registry: ExampleRegistry | None = None,
) -> str:
    """
    Render a list of DocNode into markdown text with heading hierarchy.

    Nodes at or above max_sidebar_depth render as headings.
    Nodes below max_sidebar_depth render as a fields table under their parent.
    """
    if registry is None:
        registry = ExampleRegistry([])

    md = MarkdownBuilder()

    for node in nodes:
        node_path = f"{path}.{node.title}" if path else node.title
        effective_depth = depth if depth <= max_sidebar_depth else 5

        # Heading
        md.heading(min(effective_depth, 6), node.title)

        # Description (from FieldInfo or model docstring for variants)
        if node.is_discriminated_variant:
            docstring = _get_model_docstring(node.type_annotation)
            if docstring:
                md.paragraph(docstring)
        elif node.description:
            md.paragraph(_clean_description(node.description))

        # YAML example from registry
        example_yaml = registry.render_example(node_path)
        if example_yaml:
            md.code_block(example_yaml)

        # Children
        if node.children:
            next_depth = depth + 1 if depth < 6 else 6

            if next_depth > max_sidebar_depth:
                # Render children as a fields table (below sidebar visibility)
                non_variant_children = [c for c in node.children if not c.is_discriminated_variant]
                variant_children = [c for c in node.children if c.is_discriminated_variant]

                table_rows = _render_fields_table(non_variant_children, parent_path=node_path)
                if table_rows:
                    md.table(["Key", "Description", "Status"], table_rows)

                # Recursively render nested complex fields below the table
                _render_nested_fields(non_variant_children, md, registry, node_path)

                # Render discriminated variant children with tabs
                _render_variants_as_tabs(variant_children, md, registry, node_path, parent_title=node.title)
            else:
                # Render children as headings (within sidebar visibility)
                md.line(
                    render_tree(
                        node.children,
                        depth=next_depth,
                        path=node_path,
                        max_sidebar_depth=max_sidebar_depth,
                        registry=registry,
                    )
                )

    return md.build()


def _clean_description(desc: str) -> str:
    """Remove internal documentation URL references from descriptions."""
    # Remove lines like "\n\n$ECALC_DOCS_KEYWORDS_URL/..."
    desc = re.sub(r"\n\n\$ECALC_DOCS_KEYWORDS_URL\S*", "", desc)
    # Remove inline references
    desc = re.sub(r"\$ECALC_DOCS_KEYWORDS_URL\S*", "", desc)
    return desc.strip()


def _get_model_docstring(model: Any) -> str | None:
    """Get the docstring of a model class."""
    if isinstance(model, type) and model.__doc__:
        return inspect.cleandoc(model.__doc__)
    return None


def generate_markdown() -> str:
    """Generate the full markdown document for the YAML Asset reference."""
    tree = build_yaml_asset_tree()

    frontmatter = """\
---
title: Process Reference (Experimental)
sidebar_position: 6
toc_max_heading_level: 4
description: Complete reference for the YAML Asset process configuration (DEFINITIONS, INLET_STREAMS, PROCESS_PIPELINES, PROCESS_SIMULATIONS).
---
"""

    intro = """\
import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

# Process Reference

This page documents the YAML configuration keys for the eCalc Asset model, covering the following top-level sections:

- [DEFINITIONS](#definitions)
- [INLET_STREAMS](#inlet_streams)
- [PROCESS_PIPELINES](#process_pipelines)
- [PROCESS_SIMULATIONS](#process_simulations)

"""

    registry = ExampleRegistry(EXAMPLES)

    body_parts = []
    for node in tree:
        max_depth = SIDEBAR_DEPTH.get(node.name, 2)
        body_parts.append(render_tree([node], depth=2, max_sidebar_depth=max_depth, registry=registry))

    body = "\n".join(body_parts)

    return frontmatter + "\n" + intro + body


def main():
    output_path = Path(__file__).parent.parent / "docs" / "docs" / "about" / "process-reference.mdx"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    content = generate_markdown()
    output_path.write_text(content)
    print(f"Generated: {output_path}")


if __name__ == "__main__":
    main()
