"""
Generate process and energy reference documentation from pydantic models.

Two-step process:
1. Build a tree of DocNode objects by introspecting the YamlAsset pydantic model.
2. Render the trees into single-page Docusaurus markdown documents.

Usage:
    uv run python src/generate_yaml_asset_docs.py
"""

from __future__ import annotations

import inspect
import json
import re
import types
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any, Literal, Union, get_args, get_origin

import yaml
from pydantic import BaseModel
from pydantic.fields import FieldInfo
from pydantic_core import PydanticUndefined

from energy_mermaid import (
    CATEGORIES,
    CATEGORY_CONSUMER,
    CATEGORY_PROVIDER,
    CATEGORY_SOURCE,
    generate_energy_components_mermaid,
)
from libecalc.common.version import Version
from libecalc.presentation.yaml.yaml_types.components.yaml_asset import YamlAsset, YamlDefinitions
from libecalc.presentation.yaml.yaml_types.energy.yaml_energy_network import YamlEnergySourceType
from libecalc.presentation.yaml.yaml_types.process.yaml_process_pipeline import YamlCompressorProcessUnitInstance
from libecalc.presentation.yaml.yaml_types.process.yaml_process_references import DefinitionReference
from libecalc.presentation.yaml.yaml_types.yaml_compressor import YamlCompressor
from libecalc.presentation.yaml.yaml_types.yaml_shaft import YamlShaft
from libecalc.presentation.yaml.yaml_types.yaml_version import (
    V1,
    YamlElementLifecycle,
    get_model_lifecycle,
    get_yaml_element_lifecycle,
)
from libecalc.testing.energy_builders import (
    YamlCompressorSampledBuilder,
    YamlDieselConsumerBuilder,
    YamlDriveTrainBuilder,
    YamlElectricalBusBuilder,
    YamlElectricalCableBuilder,
    YamlElectricalConsumerBuilder,
    YamlElectricalMotorBuilder,
    YamlEnergyGeneratorBuilder,
    YamlEnergyNetworkBuilder,
    YamlEnergySourceBuilder,
    YamlFileBuilder,
    YamlFuelGasConsumerBuilder,
    YamlFuelGasManifoldBuilder,
    YamlGasTurbineBuilder,
    YamlGeneratorCurveBuilder,
    YamlGeneratorDefinitionBuilder,
    YamlMechanicalConsumerBuilder,
    YamlTurbineCurveBuilder,
    YamlTurbineDefinitionBuilder,
)
from libecalc.testing.process_builders import (
    YamlCommonStreamDistributionBuilder,
    YamlCompositionFluidDefinitionBuilder,
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
    YamlTimelineBuilder,
)
from libecalc.version import current_yaml_version

# YamlAsset fields to document, as dot-separated python attribute paths.
# A top-level name includes the whole field; a dotted path (e.g. "definitions.turbines")
# includes only that sub-field, so a section can be split across documents.
PROCESS_INCLUDE_FIELDS = {
    "definitions.compressor_models",
    "definitions.fluids",
    "shafts",
    "compressors",
    "process_pipelines",
    "inlet_streams",
    "process_simulations",
    "timeline",
}
ENERGY_INCLUDE_FIELDS = {
    "definitions.turbines",
    "definitions.generators",
    "energy_network",
}

# Maximum recursion depth to prevent infinite loops on circular references
MAX_DEPTH = 8


class Example:
    """
    An example YAML snippet associated with a path in the documentation tree.

    Attributes:
        path: Dot-separated YAML key path (e.g. "PROCESS_PIPELINES.PROCESS_UNITS.PRESSURE_DROPPER").
              For discriminated union variants, the variant name is used as the last segment.
        builder: A callable that returns a validated pydantic model instance.
        abbreviate: Whether fields with their own registered example are shown as '...'.
              Disable to show a complete example, e.g. a whole network.
    """

    def __init__(self, path: str, builder: Callable, abbreviate: bool = True):
        self.path = path
        self.builder = builder
        self.abbreviate = abbreviate

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
    # --- DEFINITIONS.COMPRESSOR_MODELS ---
    Example(
        "DEFINITIONS.COMPRESSOR_MODELS",
        lambda: YamlCompressorModelChartBuilder().with_test_data().validate(),
    ),
    Example(
        "DEFINITIONS.COMPRESSOR_MODELS.CHART",
        lambda: YamlCompressorChartBuilder().with_test_data().validate(),
    ),
    Example(
        "DEFINITIONS.COMPRESSOR_MODELS.CHART.CURVES.YAMLCURVE",
        lambda: YamlCurveBuilder().with_test_data().validate(),
    ),
    # --- PROCESS_PIPELINES.PROCESS_UNITS variants ---
    Example(
        "PROCESS_PIPELINES.PROCESS_UNITS.COMPRESSOR",
        lambda: YamlCompressorProcessUnitInstance.model_validate(
            {"TYPE": "COMPRESSOR", "COMPRESSOR": "default_compressor", "MODEL": "default_compressor_model"}
        ),
    ),
    Example(
        "PROCESS_PIPELINES.PROCESS_UNITS.PRESSURE_DROPPER",
        lambda: YamlPressureDropperBuilder().with_test_data().validate(),
    ),
    Example(
        "PROCESS_PIPELINES.PROCESS_UNITS.TEMPERATURE_SETTER",
        lambda: YamlTemperatureSetterBuilder().with_test_data().validate(),
    ),
    Example(
        "PROCESS_PIPELINES.PROCESS_UNITS.LIQUID_REMOVER",
        lambda: YamlLiquidRemoverBuilder().with_test_data().validate(),
    ),
    Example(
        "PROCESS_PIPELINES.PROCESS_UNITS.MIXER",
        lambda: YamlMixerBuilder().with_test_data().validate(),
    ),
    Example(
        "PROCESS_PIPELINES.PROCESS_UNITS.SPLITTER",
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
    # --- SHAFTS ---
    Example(
        "SHAFTS",
        lambda: YamlShaft(name="default_shaft", compressors=["default_compressor"]),
    ),
    # --- COMPRESSORS ---
    Example(
        "COMPRESSORS",
        lambda: YamlCompressor(name="default_compressor", alias="RIA"),
    ),
    # --- PROCESS_PIPELINES ---
    Example(
        "PROCESS_PIPELINES",
        lambda: (
            YamlProcessPipelineBuilder()
            .with_name("DefaultPipeline")
            .with_item(YamlPressureDropperBuilder().with_test_data().validate())
            .with_item(YamlTemperatureSetterBuilder().with_test_data().validate())
            .with_item(YamlLiquidRemoverBuilder().with_test_data().validate())
            .with_compressor_item(compressor="default_compressor", model="default_compressor_model")
            .validate()
        ),
        abbreviate=False,
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
    # --- TIMELINE ---
    Example(
        "TIMELINE",
        lambda: YamlTimelineBuilder().with_test_data().validate(),
    ),
]

# ---------------------------------------------------------------------------
# Energy network examples, rendered by generate_energy_markdown().
# ---------------------------------------------------------------------------

ENERGY_EXAMPLES: list[Example] = [
    # --- DEFINITIONS.TURBINES ---
    Example(
        "DEFINITIONS.TURBINES",
        lambda: YamlTurbineDefinitionBuilder().with_test_data().validate(),
        abbreviate=False,
    ),
    Example(
        "DEFINITIONS.TURBINES.CURVE.TURBINECURVE",
        lambda: YamlTurbineCurveBuilder().with_test_data().validate(),
    ),
    Example(
        "DEFINITIONS.TURBINES.CURVE.YAMLFILE",
        lambda: YamlFileBuilder().with_test_data().validate(),
    ),
    # --- DEFINITIONS.GENERATORS ---
    Example(
        "DEFINITIONS.GENERATORS",
        lambda: YamlGeneratorDefinitionBuilder().with_test_data().validate(),
        abbreviate=False,
    ),
    Example(
        "DEFINITIONS.GENERATORS.CURVE.GENERATORCURVE",
        lambda: YamlGeneratorCurveBuilder().with_test_data().validate(),
    ),
    Example(
        "DEFINITIONS.GENERATORS.CURVE.YAMLFILE",
        lambda: YamlFileBuilder().with_file("generator_curve.csv").validate(),
    ),
    # --- ENERGY_NETWORK ---
    Example(
        "ENERGY_NETWORK",
        lambda: (
            YamlEnergyNetworkBuilder()
            .with_sources(
                [
                    YamlEnergySourceBuilder().with_test_data().validate(),
                    YamlEnergySourceBuilder()
                    .with_name("power_from_shore")
                    .with_type(YamlEnergySourceType.ELECTRICAL_SOURCE)
                    .validate(),
                ]
            )
            .with_units(
                [
                    YamlEnergyGeneratorBuilder().with_test_data().validate(),
                    YamlElectricalCableBuilder().with_test_data().validate(),
                    YamlElectricalBusBuilder().with_test_data().validate(),
                    YamlElectricalConsumerBuilder().with_test_data().validate(),
                    YamlGasTurbineBuilder().with_test_data().validate(),
                    YamlDriveTrainBuilder().with_test_data().validate(),
                ]
            )
            .validate()
        ),
        abbreviate=False,
    ),
    Example(
        "ENERGY_NETWORK.SOURCES",
        lambda: YamlEnergySourceBuilder().with_test_data().with_capacity(50000).validate(),
    ),
    # --- ENERGY_NETWORK.UNITS variants ---
    Example(
        "ENERGY_NETWORK.UNITS.GENERATOR",
        lambda: YamlEnergyGeneratorBuilder().with_test_data().validate(),
    ),
    Example(
        "ENERGY_NETWORK.UNITS.GAS_TURBINE",
        lambda: YamlGasTurbineBuilder().with_test_data().validate(),
    ),
    Example(
        "ENERGY_NETWORK.UNITS.ELECTRICAL_MOTOR",
        lambda: YamlElectricalMotorBuilder().with_test_data().validate(),
    ),
    Example(
        "ENERGY_NETWORK.UNITS.ELECTRICAL_CABLE",
        lambda: YamlElectricalCableBuilder().with_test_data().validate(),
    ),
    Example(
        "ENERGY_NETWORK.UNITS.ELECTRICAL_BUS",
        lambda: YamlElectricalBusBuilder().with_test_data().validate(),
    ),
    Example(
        "ENERGY_NETWORK.UNITS.FUEL_GAS_MANIFOLD",
        lambda: YamlFuelGasManifoldBuilder().with_test_data().validate(),
    ),
    Example(
        "ENERGY_NETWORK.UNITS.ELECTRICAL_CONSUMER",
        lambda: YamlElectricalConsumerBuilder().with_test_data().validate(),
    ),
    Example(
        "ENERGY_NETWORK.UNITS.ELECTRICAL_CONSUMER.LOAD.CURVE.POWERCURVE",
        lambda: (
            YamlElectricalConsumerBuilder()
            .with_test_data()
            .with_load_curve({"variable": [0, 1000, 5000], "power": [0, 0.8, 3.4]}, "SIM;RATE")
            .validate()
            .load
        ),
    ),
    Example(
        "ENERGY_NETWORK.UNITS.ELECTRICAL_CONSUMER.LOAD.CURVE.YAMLFILE",
        lambda: (
            YamlElectricalConsumerBuilder()
            .with_test_data()
            .with_load_curve({"file": "pump_sampled.csv"}, "SIM;RATE")
            .validate()
            .load
        ),
    ),
    Example(
        "ENERGY_NETWORK.UNITS.MECHANICAL_CONSUMER",
        lambda: YamlMechanicalConsumerBuilder().with_test_data().validate(),
    ),
    Example(
        "ENERGY_NETWORK.UNITS.MECHANICAL_CONSUMER.LOAD.CURVE.POWERCURVE",
        lambda: (
            YamlMechanicalConsumerBuilder()
            .with_test_data()
            .with_load_curve({"variable": [0, 1000, 5000], "power": [0, 0.8, 3.4]}, "SIM;RATE")
            .validate()
            .load
        ),
    ),
    Example(
        "ENERGY_NETWORK.UNITS.MECHANICAL_CONSUMER.LOAD.CURVE.YAMLFILE",
        lambda: (
            YamlMechanicalConsumerBuilder()
            .with_test_data()
            .with_load_curve({"file": "pump_sampled.csv"}, "SIM;RATE")
            .validate()
            .load
        ),
    ),
    Example(
        "ENERGY_NETWORK.UNITS.DRIVE_TRAIN",
        lambda: YamlDriveTrainBuilder().with_test_data().validate(),
    ),
    Example(
        "ENERGY_NETWORK.UNITS.FUEL_GAS_CONSUMER",
        lambda: YamlFuelGasConsumerBuilder().with_test_data().validate(),
    ),
    Example(
        "ENERGY_NETWORK.UNITS.FUEL_GAS_CONSUMER.RATE.CURVE.FUELTABLE",
        lambda: (
            YamlFuelGasConsumerBuilder()
            .with_test_data()
            .with_rate_curve({"variable": [0, 1000, 5000], "fuel": [0, 8000, 35000]}, "SIM;RATE")
            .validate()
            .rate
        ),
    ),
    Example(
        "ENERGY_NETWORK.UNITS.FUEL_GAS_CONSUMER.RATE.CURVE.YAMLFILE",
        lambda: (
            YamlFuelGasConsumerBuilder()
            .with_test_data()
            .with_rate_curve({"file": "flare_sampled.csv"}, "SIM;RATE")
            .validate()
            .rate
        ),
    ),
    Example(
        "ENERGY_NETWORK.UNITS.DIESEL_CONSUMER",
        lambda: YamlDieselConsumerBuilder().with_test_data().validate(),
    ),
    Example(
        "ENERGY_NETWORK.UNITS.DIESEL_CONSUMER.RATE.CURVE.FUELTABLE",
        lambda: (
            YamlDieselConsumerBuilder()
            .with_test_data()
            .with_rate_curve({"variable": [0, 1000, 5000], "fuel": [0, 8000, 35000]}, "SIM;RATE")
            .validate()
            .rate
        ),
    ),
    Example(
        "ENERGY_NETWORK.UNITS.DIESEL_CONSUMER.RATE.CURVE.YAMLFILE",
        lambda: (
            YamlDieselConsumerBuilder()
            .with_test_data()
            .with_rate_curve({"file": "flare_sampled.csv"}, "SIM;RATE")
            .validate()
            .rate
        ),
    ),
    Example(
        "ENERGY_NETWORK.UNITS.COMPRESSOR_SAMPLED",
        lambda: YamlCompressorSampledBuilder().with_test_data().validate(),
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
        if child_paths and example.abbreviate:
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

    @property
    def available_since(self) -> Version:
        """The yaml schema version this element became available in, defaulting to V1."""
        lifecycle = self.lifecycle
        return lifecycle.available_since if lifecycle is not None else V1

    @property
    def lifecycle(self) -> YamlElementLifecycle | None:
        """The element's lifecycle (available/deprecated/removed since), if it has one.

        Root elements and ordinary nested fields carry their lifecycle on the pydantic
        Field(...) itself. Discriminated union variants (e.g. a TYPE-based Tabs entry)
        aren't a Field, so their lifecycle is read from the variant model's own
        model_config instead — see get_model_lifecycle().
        """
        if self.field_info is not None:
            return get_yaml_element_lifecycle(self.field_info)
        if self.is_discriminated_variant and isinstance(self.type_annotation, type):
            return get_model_lifecycle(self.type_annotation)
        return None

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
            for model in _get_inner_models(arg):
                if model not in models:
                    models.append(model)
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


def _get_discriminator_field_name(annotation: Any) -> str | None:
    """Extract the discriminator field name from a Field(discriminator=...) annotation."""
    if get_origin(annotation) is Annotated:
        for arg in get_args(annotation)[1:]:
            discriminator = getattr(arg, "discriminator", None)
            if discriminator:
                return discriminator
    return None


def _get_discriminator_value(model: type[BaseModel], discriminator_field: str | None = None) -> str | None:
    """
    Extract the discriminator value from a model's Literal type field.

    For example, if the model has `type: Literal["COMPRESSOR"]`, returns "COMPRESSOR".
    If discriminator_field is given, that field name is used; otherwise falls back to
    the common discriminator field names: 'type', 'method'.
    """
    field_names = (discriminator_field,) if discriminator_field else ("type", "method")
    for field_name in field_names:
        if not field_name or field_name not in model.model_fields:
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
        include_fields: If provided, only include these fields. Entries are dot-separated
            python attribute paths: "definitions" includes the whole field, while
            "definitions.turbines" includes only the turbines sub-field of definitions.
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
        child_include_fields: set[str] | None = None
        if include_fields:
            if field_name in include_fields:
                child_include_fields = None
            else:
                prefix = field_name + "."
                child_include_fields = {p.removeprefix(prefix) for p in include_fields if p.startswith(prefix)}
                if not child_include_fields:
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
                discriminator_field = _get_discriminator_field_name(annotation)
                seen_variant_names: set[str] = set()
                for variant_model in inner_models:
                    variant_name = (
                        _get_discriminator_value(variant_model, discriminator_field)
                        or variant_model.model_config.get("title")
                        or variant_model.__name__
                    )
                    if variant_name in seen_variant_names:
                        variant_name = variant_model.__name__
                    seen_variant_names.add(variant_name)
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
                node.children = build_tree(
                    inner_models[0],
                    include_fields=child_include_fields,
                    _depth=_depth + 1,
                    _seen=_seen,
                )

        nodes.append(node)

    return nodes


def build_yaml_asset_tree(include_fields: set[str] | None) -> list[DocNode]:
    """Build a documentation tree for selected YamlAsset sections, or the whole model if include_fields is None."""
    return build_tree(YamlAsset, include_fields=include_fields)


# --- Step 2: Render tree to markdown ---


# Maximum heading level to show in sidebar TOC, per top-level field name.
# h2=top-level, h3=one below, h4=two below. Anything deeper uses h5+ (hidden from sidebar).
SIDEBAR_DEPTH: dict[str, int] = {
    "definitions": 4,  # DEFINITIONS > FLUIDS > PREDEFINED (h2, h3, h4)
    "inlet_streams": 2,  # INLET_STREAMS only (h2)
    "shafts": 2,  # SHAFTS only (h2)
    "compressors": 2,  # COMPRESSORS only (h2)
    "process_pipelines": 2,  # PROCESS_PIPELINES only (h2)
    "process_simulations": 2,  # PROCESS_SIMULATIONS only (h2)
    "timeline": 2,  # TIMELINE only (h2)
    "energy_network": 3,  # ENERGY_NETWORK only (h2)
}


class MarkdownBuilder:
    def __init__(self):
        self._lines: list[str] = []

    def heading(self, level: int, text: str, suffix: str = "", anchor: str | None = None) -> MarkdownBuilder:
        heading_text = f"{text} {suffix}" if suffix else text
        if anchor:
            # MDX v2+ requires escaping the opening brace of a custom heading id: \{#id}
            # See https://mdxjs.com/docs/troubleshooting-mdx/#could-not-parse-expression-with-acorn-error
            heading_text = f"{heading_text} \\{{#{anchor}}}"
        self._lines.append(f"{'#' * level} {heading_text}")
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
        if language == "yaml":
            # Rendered with indent guides. Emitted as a single-line JS string literal: MDX strips
            # leading whitespace from continuation lines of multi-line JSX expressions, which
            # would corrupt the YAML indentation.
            self._lines.append("<YamlCodeBlock>{" + json.dumps(code) + "}</YamlCodeBlock>")
        else:
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
    subsection (e.g. YamlPredefinedFluidDefinition -> "FLUIDS").
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

    Returns the subsection title (e.g. "FLUIDS", "TURBINES") or None.
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
    """Generate a URL-friendly anchor from a path, used as an explicit Docusaurus heading id
    (`{#anchor}`) so headings keep a stable, predictable id regardless of their content,
    including inline <LifecycleBadge> JSX, which otherwise breaks automatic heading-id slugging."""
    return path.lower().replace(".", "-")


def _lifecycle_badges_markdown(lifecycle: YamlElementLifecycle | None) -> str:
    """Render inline <LifecycleBadge> tags for a node's lifecycle, to append to its heading."""
    if lifecycle is None:
        return ""
    badges = []
    if lifecycle.available_since > V1:
        badges.append(f'<LifecycleBadge kind="introduced" version="{lifecycle.available_since.major}" />')
    if lifecycle.deprecated_since is not None:
        badges.append(f'<LifecycleBadge kind="deprecated" version="{lifecycle.deprecated_since.major}" />')
    if lifecycle.removed_since is not None:
        badges.append(f'<LifecycleBadge kind="removed" version="{lifecycle.removed_since.major}" />')
    return " ".join(badges)


def _escape_jsx_string(value: str) -> str:
    """Escape a string for embedding as a JSX string literal inside a f-string-built prop."""
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _change_history_markdown(lifecycle: YamlElementLifecycle | None) -> str:
    """Render an inline <ChangeHistory> listing a node's changed_in entries, if any."""
    if lifecycle is None or not lifecycle.changed_in:
        return ""
    changes = ", ".join(
        f'{{ "version": "{change.version.major}", "description": "{_escape_jsx_string(change.description)}" }}'
        for change in lifecycle.changed_in
    )
    return f"<ChangeHistory changes={{[{changes}]}} />"


def _lifecycle_markup(lifecycle: YamlElementLifecycle | None) -> str:
    """Render the combined lifecycle badges and change history for a node, to append to its heading
    or key cell."""
    parts = [part for part in (_lifecycle_badges_markdown(lifecycle), _change_history_markdown(lifecycle)) if part]
    return " ".join(parts)


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

        badges = _lifecycle_markup(node.lifecycle)
        if badges:
            key_cell = f"{key_cell} {badges}"

        rows.append([key_cell, desc, status])
    return rows


def _render_variants_as_tabs(
    variant_children: list[DocNode],
    md: MarkdownBuilder,
    registry: ExampleRegistry,
    parent_path: str,
    parent_title: str | None = None,
    parent_lifecycle: YamlElementLifecycle | None = None,
    anchor_registry: dict[str, str] | None = None,
) -> None:
    """Render discriminated union variants inside Docusaurus Tabs."""
    if not variant_children:
        return

    if parent_title:
        anchor = _make_field_anchor(parent_path)
        if anchor_registry is not None:
            anchor_registry[parent_path] = anchor
        badges = _lifecycle_markup(parent_lifecycle)
        suffix = f" {badges}" if badges else ""
        md.line(f"##### {parent_title}{suffix} \\{{#{anchor}}}")
        md.line("")

    md.tabs_start()
    for variant in variant_children:
        variant_path = f"{parent_path}.{variant.title}"
        md.tab_item_start(label=variant.title)

        # Scope div: lets the browser-side LifecycleFilter know this variant's own
        # lifecycle (if any), so fields inside it without their own badge still filter
        # correctly by inheriting from the variant rather than only the group heading.
        # `display: contents` (see custom.css) keeps it invisible as a layout box.
        md.line('<div className="lifecycle-variant">')
        md.line("")
        badges = _lifecycle_markup(variant.lifecycle)
        if badges:
            md.paragraph(badges)

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
            _render_nested_fields(variant_non_variant, md, registry, variant_path, anchor_registry=anchor_registry)

        md.line("")
        md.line("</div>")
        md.tab_item_end()
    md.tabs_end()


def _render_nested_fields(
    nodes: list[DocNode],
    md: MarkdownBuilder,
    registry: ExampleRegistry,
    parent_path: str,
    anchor_registry: dict[str, str] | None = None,
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
            if anchor_registry is not None:
                anchor_registry[node_path] = anchor
            badges = _lifecycle_markup(node.lifecycle)
            suffix = f" {badges}" if badges else ""
            md.line(f"##### {node.title}{suffix} \\{{#{anchor}}}")
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
            _render_nested_fields(non_variant_children, md, registry, node_path, anchor_registry=anchor_registry)

        # Render discriminated union variants with tabs
        if variant_children:
            _render_variants_as_tabs(
                variant_children,
                md,
                registry,
                node_path,
                parent_title=node.title,
                parent_lifecycle=node.lifecycle,
                anchor_registry=anchor_registry,
            )


def render_tree(
    nodes: list[DocNode],
    depth: int = 2,
    path: str = "",
    max_sidebar_depth: int = 6,
    registry: ExampleRegistry | None = None,
    anchor_registry: dict[str, str] | None = None,
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

        # Heading. Anchor matches Docusaurus's default auto-slug (lowercased title) so
        # existing cross-references (e.g. "#process_units", "#definitions") keep working;
        # it must be explicit because inline <LifecycleBadge> JSX breaks auto-slugging.
        anchor = node.title.lower()
        if anchor_registry is not None:
            anchor_registry[node_path] = anchor
        md.heading(
            min(effective_depth, 6),
            node.title,
            suffix=_lifecycle_markup(node.lifecycle),
            anchor=anchor,
        )

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
                _render_nested_fields(non_variant_children, md, registry, node_path, anchor_registry=anchor_registry)

                # Render discriminated variant children with tabs
                _render_variants_as_tabs(
                    variant_children,
                    md,
                    registry,
                    node_path,
                    parent_title=node.title,
                    parent_lifecycle=node.lifecycle,
                    anchor_registry=anchor_registry,
                )
            else:
                # Render children as headings (within sidebar visibility)
                md.line(
                    render_tree(
                        node.children,
                        depth=next_depth,
                        path=node_path,
                        max_sidebar_depth=max_sidebar_depth,
                        registry=registry,
                        anchor_registry=anchor_registry,
                    )
                )

    return md.build()


def _clean_description(desc: str) -> str:
    """Remove internal documentation URL references from descriptions."""
    # Remove lines like "\n\n$ECALC_DOCS_KEYWORDS_URL/..."
    desc = re.sub(r"\n\n\$ECALC_DOCS_KEYWORDS_URL\S*", "", desc)
    # Remove inline references
    desc = re.sub(r"\$ECALC_DOCS_KEYWORDS_URL\S*", "", desc)
    # Escape angle brackets so MDX doesn't interpret them as JSX tags
    desc = desc.replace("<", "&lt;").replace(">", "&gt;")
    return desc.strip()


def _get_model_docstring(model: Any) -> str | None:
    """Get the docstring of a model class."""
    if isinstance(model, type) and model.__doc__:
        return inspect.cleandoc(model.__doc__)
    return None


def _generate_markdown(
    *,
    include_fields: set[str] | None,
    title: str,
    sidebar_position: int,
    description: str,
    intro: str,
    examples: list[Example],
    anchor_registry: dict[str, str] | None = None,
) -> str:
    """Generate a reference document for selected YamlAsset sections, or the whole model if include_fields is None."""
    tree = build_yaml_asset_tree(include_fields)

    frontmatter = f"""\
---
title: {title} (Experimental)
sidebar_position: {sidebar_position}
toc_max_heading_level: 4
description: {description}
---
"""

    imports = """\
import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';
import YamlCodeBlock from '@site/src/components/YamlCodeBlock';
import LifecycleBadge from '@site/src/components/LifecycleBadge';
import LifecycleFilter from '@site/src/components/LifecycleFilter';
import ChangeHistory from '@site/src/components/ChangeHistory';

"""

    versions = ", ".join(str(major) for major in range(V1.major, current_yaml_version().major + 1))

    legend = (
        "Elements are labelled with their lifecycle: "
        '<LifecycleBadge kind="introduced" version="N" />'
        '<LifecycleBadge kind="deprecated" version="N" />'
        '<LifecycleBadge kind="removed" version="N" />. '
        "Elements with a behavioral change also show an expandable `Changed in:` label you can "
        "click to see what changed.\n\n"
        "Use the filter below to show only the elements available for a single YAML_VERSION.\n\n"
        f"<LifecycleFilter versions={{[{versions}]}} />\n\n"
    )

    registry = ExampleRegistry(examples)

    body_parts = []
    for node in tree:
        max_depth = SIDEBAR_DEPTH.get(node.name, 2)
        section = render_tree(
            [node], depth=2, max_sidebar_depth=max_depth, registry=registry, anchor_registry=anchor_registry
        )
        body_parts.append(section)

    body = "\n".join(body_parts)

    return frontmatter + "\n" + imports + intro + legend + body


def _time_series_section(opening: str, closing: str = "") -> str:
    return f"""\
## Time steps and time series

{opening} These time steps come from the time series files and dated `VARIABLES` it uses, and from the `FROM` dates in `TIMELINE.EVENTS`: all dates are merged into one time vector.{closing}

A value from a time series applies from its date until the next date in that file (forward-fill). After a file's last date, its last value is kept until `END`. Dated `VARIABLES` work the same way. Each file and dated variable must have a value at `START`, otherwise the run fails.

**When to resample yourself**

Forward-fill fits inputs that hold steady between dates, such as rates or on/off states. Inputs that change gradually between dates, such as pressures, should carry the intermediate values in the file itself.

> `INTERPOLATION_TYPE`, `EXTRAPOLATION` and `INFLUENCE_TIME_VECTOR` have no effect on time series referenced here.

"""


def generate_process_markdown() -> str:
    """Generate the process reference document."""
    return _generate_markdown(
        include_fields=PROCESS_INCLUDE_FIELDS,
        title="Process Reference",
        sidebar_position=1,
        description="Complete reference for the process configuration.",
        intro="""\
# Process Reference

This page documents the YAML configuration keys for the eCalc Asset model, covering the following top-level sections:

- [DEFINITIONS](#definitions)
- [INLET_STREAMS](#inlet_streams)
- [SHAFTS](#shafts)
- [COMPRESSORS](#compressors)
- [PROCESS_PIPELINES](#process_pipelines)
- [PROCESS_SIMULATIONS](#process_simulations)
- [TIMELINE](#timeline)

"""
        + _time_series_section(
            "Each process simulation is calculated on its own time steps, between `START` and `END`."
        ),
        examples=EXAMPLES,
    )


def generate_energy_markdown() -> str:
    """Generate the energy network reference document."""
    return _generate_markdown(
        include_fields=ENERGY_INCLUDE_FIELDS,
        title="Energy Reference",
        sidebar_position=2,
        description="Complete reference for the energy network configuration.",
        intro="""\
# Energy Reference

This page documents the energy related YAML configuration keys for the eCalc Asset model, covering the following top-level sections:

- [DEFINITIONS](#definitions)
- [ENERGY_NETWORK](#energy_network)

"""
        + _time_series_section(
            "The energy network is calculated on time steps between `START` and `END`.",
            " Dates from process simulations used by the energy network are also included.",
        ),
        examples=ENERGY_EXAMPLES,
    )


def generate_full_reference_markdown(anchor_registry: dict[str, str] | None = None) -> str:
    """Generate a single reference document covering every YamlAsset root element, across all yaml versions.

    If given, anchor_registry is populated with a dot-separated element path -> in-page anchor
    mapping, so other pages (e.g. the yaml changelog) can link straight to the relevant section.
    """
    return _generate_markdown(
        include_fields=None,
        title="YAML Reference",
        sidebar_position=3,
        description="Complete reference for all YAML configuration keys, across every schema version.",
        intro="""\
# YAML Reference

This page documents every YAML configuration key for the eCalc Asset model, regardless of `YAML_VERSION`.

Use the version filter below to show only the elements available for a chosen `YAML_VERSION`.

""",
        examples=EXAMPLES + ENERGY_EXAMPLES,
        anchor_registry=anchor_registry,
    )


# ---------------------------------------------------------------------------
# YAML changelog
#
# One page per yaml major version, listing which elements were added,
# deprecated or removed in that version specifically, to help users migrate
# their own models. V1 and V2 predate this changelog and are intentionally
# left out — add new versions here as they're introduced.
# ---------------------------------------------------------------------------

FIRST_YAML_CHANGELOG_VERSION = Version(current_yaml_version().major - 1, 0, 0)  # 1 version back (current + previous)

YAML_CHANGELOG_VERSIONS: list[Version] = [
    Version(major, 0, 0) for major in range(FIRST_YAML_CHANGELOG_VERSION.major, current_yaml_version().major + 1)
]


def _release_label(version: Version) -> str:
    status = "In development" if version.major == current_yaml_version().major else "In production"
    return f"{status} (v{version.major})"


ChangeKind = Literal["added", "deprecated", "removed", "changed"]


@dataclass
class ChangelogEntry:
    path: list[str]
    kind: ChangeKind
    description: str | None = None
    replaced_by: tuple[tuple[str, ...], ...] = ()


def _node_event_major(node: DocNode, kind: ChangeKind) -> int | None:
    """The major version a node's lifecycle event (added/deprecated/removed) happened in, if any."""
    lifecycle = node.lifecycle
    if lifecycle is None:
        return None
    if kind == "added":
        return lifecycle.available_since.major
    if kind == "deprecated":
        return lifecycle.deprecated_since.major if lifecycle.deprecated_since else None
    return lifecycle.removed_since.major if lifecycle.removed_since else None


def _collect_changelog_entries(
    nodes: list[DocNode],
    version: int,
    path: list[str],
    covered: frozenset[ChangeKind] = frozenset(),
) -> list[ChangelogEntry]:
    """
    Walk the full documentation tree, collecting the lifecycle events (added/deprecated/removed)
    that happened in the given yaml major version.

    If a whole element was itself added/deprecated/removed in this version, its descendants
    aren't listed individually for that same kind of event — it's implied by the parent.
    """
    entries: list[ChangelogEntry] = []
    for node in nodes:
        node_path = [*path, node.title]
        node_covered = set(covered)
        for kind in ("added", "deprecated", "removed"):
            if kind in covered:
                continue
            if _node_event_major(node, kind) == version:
                replaced_by = node.lifecycle.replaced_by if kind == "removed" and node.lifecycle else ()
                entries.append(ChangelogEntry(path=node_path, kind=kind, replaced_by=replaced_by))
                node_covered.add(kind)
        if "changed" not in covered:
            lifecycle = node.lifecycle
            for change in lifecycle.changed_in if lifecycle is not None else ():
                if change.version.major == version:
                    entries.append(ChangelogEntry(path=node_path, kind="changed", description=change.description))
                    node_covered.add("changed")
        entries.extend(_collect_changelog_entries(node.children, version, node_path, frozenset(node_covered)))
    return entries


def _resolve_reference_anchor(path: list[str], anchor_registry: dict[str, str]) -> str | None:
    """
    Resolve the yaml-reference.mdx anchor for a changelog entry's element path.

    Tries the exact path first, then progressively shorter prefixes, since not every element
    (e.g. a plain leaf field, or a discriminated union variant) gets its own heading/anchor —
    falling back to the nearest ancestor that does is still a useful link.
    """
    for end in range(len(path), 0, -1):
        anchor = anchor_registry.get(".".join(path[:end]))
        if anchor is not None:
            return anchor
    return None


def _render_changelog_section(
    title: str, entries: list[ChangelogEntry], anchor_registry: dict[str, str] | None = None
) -> str:
    if not entries:
        return ""
    lines = [f"## {title}", ""]
    for entry in entries:
        breadcrumb = " › ".join(f"`{segment}`" for segment in entry.path)
        anchor = _resolve_reference_anchor(entry.path, anchor_registry) if anchor_registry is not None else None
        if anchor is not None:
            breadcrumb = f"[{breadcrumb}](../yaml-reference.mdx#{anchor})"
        if entry.description:
            breadcrumb = f"{breadcrumb}: {entry.description}"
        if entry.replaced_by:
            replacements = []
            for replacement_path in entry.replaced_by:
                replacement = " › ".join(f"`{segment}`" for segment in replacement_path)
                replacement_anchor = (
                    _resolve_reference_anchor(list(replacement_path), anchor_registry)
                    if anchor_registry is not None
                    else None
                )
                if replacement_anchor is not None:
                    replacement = f"[{replacement}](../yaml-reference.mdx#{replacement_anchor})"
                replacements.append(replacement)
            breadcrumb = f"{breadcrumb}: replaced by {' and '.join(replacements)}"
        lines.append(f"- {breadcrumb}")
    lines.append("")
    lines.append("")
    return "\n".join(lines)


def generate_yaml_changelog_markdown(version: Version, anchor_registry: dict[str, str] | None = None) -> str:
    """Generate the yaml changelog page for a single yaml major version."""
    tree = build_yaml_asset_tree(include_fields=None)
    entries = _collect_changelog_entries(tree, version.major, path=[])
    added = [e for e in entries if e.kind == "added"]
    changed = [e for e in entries if e.kind == "changed"]
    deprecated = [e for e in entries if e.kind == "deprecated"]
    removed = [e for e in entries if e.kind == "removed"]

    frontmatter = f"""\
---
title: YAML changelog, {_release_label(version)}
sidebar_label: {_release_label(version)}
sidebar_position: {version.major}
description: YAML configuration changes introduced in YAML_VERSION {version.major}.
---
"""

    body = f"""\
# YAML changelog, {_release_label(version)}

This page lists the YAML configuration changes introduced in `YAML_VERSION: {version.major}`, compared to the
previous version. See the [YAML Reference](../yaml-reference.mdx) for the full, current schema across all
versions.

"""
    sections = (
        _render_changelog_section("Added", added, anchor_registry)
        + _render_changelog_section("Changed", changed, anchor_registry)
        + _render_changelog_section("Deprecated", deprecated, anchor_registry)
        + _render_changelog_section("Removed", removed, anchor_registry)
    )
    if not sections.strip():
        sections = "No changes recorded for this version yet.\n"

    return frontmatter + "\n" + body + sections


def generate_yaml_changelog_index_markdown() -> str:
    """Generate the yaml changelog landing page, listing all covered versions."""
    links = "\n".join(f"- [{_release_label(version)}](./v{version.major}.md)" for version in YAML_CHANGELOG_VERSIONS)
    return f"""\
---
title: YAML Changelog
sidebar_position: 0
description: YAML configuration changes, by YAML_VERSION.
---

# YAML Changelog

This section lists the YAML configuration changes for each `YAML_VERSION`, to help you migrate your own model from
a previous version. Each page covers the additions, deprecations and removals introduced in that version, compared
to the previous one.

See the [YAML Reference](../yaml-reference.mdx) for the full, current schema across all versions.

{links}
"""


ENERGY_COMPONENT_CATEGORY_DETAILS: dict[str, tuple[str, str, list[str]]] = {
    CATEGORY_SOURCE: (
        "sources",
        "External energy entering the network. Sources only have an output.",
        [],
    ),
    CATEGORY_PROVIDER: (
        "providers",
        "Components that take energy in and provide energy to other components, such as converters and junctions.",
        [
            "`GENERATOR` accepts fuel gas or diesel and provides electrical power.",
            "`ELECTRICAL_BUS` and `FUEL_GAS_MANIFOLD` provide the same energy type as their inputs.",
        ],
    ),
    CATEGORY_CONSUMER: (
        "consumers",
        "Components that use energy from the network. Consumers only have an input.",
        [
            "`COMPRESSOR_SAMPLED` accepts fuel gas, electrical or mechanical energy, depending on the energy columns "
            "in its `FILE`.",
            "`DRIVE_TRAIN` accepts mechanical energy and refers to a shaft.",
        ],
    ),
}

ENERGY_COMPONENTS_DIRECTORY_NAME = "energy-components"


def generate_energy_components_index_markdown() -> str:
    links = "\n".join(
        f"- [{category}](./{ENERGY_COMPONENT_CATEGORY_DETAILS[category][0]}.mdx): "
        f"{ENERGY_COMPONENT_CATEGORY_DETAILS[category][1]}"
        for category in CATEGORIES
    )
    return f"""\
---
title: Energy Components (Experimental)
sidebar_position: 0
description: Overview of the energy components, by category, with the energy types they accept and provide.
---

# Energy Components

All energy components in the `ENERGY_NETWORK`, grouped as sources, providers and consumers. On each page, the
connections on every component are coloured by energy type: inputs show what a component accepts, outputs show what it
provides. Two components can be connected when the output colour of one matches the input colour of the next.
See the [Energy Reference](../energy-reference.mdx) for the full description of every element.

{links}
"""


def generate_energy_components_category_markdown(category: str, sidebar_position: int) -> str:
    _, description, notes = ENERGY_COMPONENT_CATEGORY_DETAILS[category]
    notes_markdown = "".join(f"- {note}\n" for note in notes)
    notes_section = f"\n{notes_markdown}" if notes else ""
    return f"""\
---
title: {category} (Experimental)
sidebar_position: {sidebar_position}
description: {description}
---

# {category}

{description} Connections are coloured by the energy type they accept or provide.

```mermaid
{generate_energy_components_mermaid(category)}
```
{notes_section}"""


def generate_energy_components_pages() -> dict[str, str]:
    pages = {"index.md": generate_energy_components_index_markdown()}
    for position, category in enumerate(CATEGORIES, start=1):
        file_stem = ENERGY_COMPONENT_CATEGORY_DETAILS[category][0]
        pages[f"{file_stem}.mdx"] = generate_energy_components_category_markdown(category, position)
    return pages


def main():
    about_dir = Path(__file__).parent.parent / "docs" / "docs" / "about" / "nextgen"
    about_dir.mkdir(parents=True, exist_ok=True)
    changelog_dir = about_dir / "yaml-changelog"
    changelog_dir.mkdir(parents=True, exist_ok=True)
    energy_components_dir = about_dir / ENERGY_COMPONENTS_DIRECTORY_NAME
    energy_components_dir.mkdir(parents=True, exist_ok=True)

    anchor_registry: dict[str, str] = {}

    outputs = {
        about_dir / "process-reference.mdx": generate_process_markdown(),
        about_dir / "energy-reference.mdx": generate_energy_markdown(),
        about_dir / "yaml-reference.mdx": generate_full_reference_markdown(anchor_registry=anchor_registry),
        changelog_dir / "index.md": generate_yaml_changelog_index_markdown(),
    }
    for file_name, content in generate_energy_components_pages().items():
        outputs[energy_components_dir / file_name] = content
    for version in YAML_CHANGELOG_VERSIONS:
        outputs[changelog_dir / f"v{version.major}.md"] = generate_yaml_changelog_markdown(
            version, anchor_registry=anchor_registry
        )

    for output_path, content in outputs.items():
        output_path.write_text(content)
        print(f"Generated: {output_path}")


if __name__ == "__main__":
    main()
