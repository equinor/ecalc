from typing import Annotated, Any, Literal, Union

from pydantic import BeforeValidator, ConfigDict, Discriminator, Field, Tag

from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.energy.yaml_generator_definition import YamlGeneratorDefinition
from libecalc.presentation.yaml.yaml_types.energy.yaml_turbine_definition import YamlTurbineDefinition
from libecalc.presentation.yaml.yaml_types.process.yaml_process_references import (
    DefinitionReference,
    validate_definition_reference_or_inline_model,
)

GENERATOR_EFFICIENCY_DESCRIPTION = "Electrical generator conversion efficiency, a fraction above 0 and up to 1."

YamlGeneratorSetEngineType = Literal["GAS_TURBINE_DRIVEN", "DIESEL_ENGINE_DRIVEN"]


class YamlGeneratorSetEngineDefinition(YamlBase):
    """A generator set driven by a combustion engine (gas turbine or diesel engine) combined with a
    generator efficiency, as opposed to a direct power-to-fuel curve."""

    model_config = ConfigDict(
        title="GeneratorSetEngineDefinition",
        json_schema_extra={
            "examples": [
                {"TYPE": "GAS_TURBINE_DRIVEN", "ENGINE": "lm2500_curve", "GENERATOR_EFFICIENCY": 0.97},
                {"TYPE": "DIESEL_ENGINE_DRIVEN", "ENGINE": "diesel_engine_curve", "GENERATOR_EFFICIENCY": 0.97},
            ],
        },
    )

    type: Annotated[
        YamlGeneratorSetEngineType,
        Field(title="TYPE", description="The combustion engine type driving the generator set."),
    ]
    engine: Annotated[
        DefinitionReference | YamlTurbineDefinition,
        validate_definition_reference_or_inline_model(YamlTurbineDefinition),
        Field(
            title="ENGINE",
            description="Engine model, given directly in place or as a reference to DEFINITIONS.PERFORMANCE_CURVES.",
        ),
    ]
    generator_efficiency: Annotated[
        float,
        Field(
            title="GENERATOR_EFFICIENCY",
            description=GENERATOR_EFFICIENCY_DESCRIPTION,
            gt=0,
            le=1,
        ),
    ]


_CURVE_MODEL_TYPE = "POWER_TO_FUEL"
_ENGINE_MODEL_TYPES = set(YamlGeneratorSetEngineType.__args__)
_KNOWN_MODEL_TYPES = {_CURVE_MODEL_TYPE, *_ENGINE_MODEL_TYPES}


def _get_type_value(data: dict[str, Any]) -> Any:
    return next((value for key, value in data.items() if str(key).lower() == "type"), None)


def _is_known_model_type(type_value: Any, known_types: set[str]) -> bool:
    """Whether type_value is one of known_types, without raising on an unhashable value (e.g. a list or dict)."""
    return isinstance(type_value, str) and type_value in known_types


def _reject_unrecognized_generator_set_model_shape(data: Any) -> Any:
    """Fail fast on a TYPE matching neither shape, instead of silently falling back to "curve".

    Without this, a typo like GAS_TURBINE_DRIVE produces a confusing "TYPE should be POWER_TO_FUEL" error
    instead of pointing at the actual mistake.
    """
    if not isinstance(data, dict):
        return data
    type_value = _get_type_value(data)
    if type_value is None or _is_known_model_type(type_value, _KNOWN_MODEL_TYPES):
        return data
    raise ValueError(
        f"Unrecognized TYPE for generator set MODEL: {type_value!r}. Expected one of "
        f"{_CURVE_MODEL_TYPE!r} or {sorted(_ENGINE_MODEL_TYPES)}."
    )


def _generator_set_model_discriminator(data: Any) -> str:
    """Route a dict to the engine shape whenever TYPE is an engine type, even if other engine fields
    (e.g. ENGINE) are missing, so pydantic reports a clear error about the actual missing/invalid field
    instead of silently falling back to the curve shape and reporting unrelated curve-field errors.
    """
    if isinstance(data, YamlGeneratorSetEngineDefinition):
        return "engine"
    if isinstance(data, (YamlGeneratorDefinition, str)):
        return "curve"
    if not isinstance(data, dict):
        return "curve"

    if _is_known_model_type(_get_type_value(data), _ENGINE_MODEL_TYPES):
        return "engine"
    return "curve"


YamlGeneratorSetModel = Annotated[
    Union[
        Annotated[
            DefinitionReference | YamlGeneratorDefinition,
            validate_definition_reference_or_inline_model(YamlGeneratorDefinition),
            Tag("curve"),
        ],
        Annotated[YamlGeneratorSetEngineDefinition, Tag("engine")],
    ],
    Discriminator(_generator_set_model_discriminator),
    BeforeValidator(_reject_unrecognized_generator_set_model_shape),
    Field(
        title="MODEL",
        description="Generator set model: either a direct power-to-fuel curve (given directly in place or as a "
        "reference to DEFINITIONS.PERFORMANCE_CURVES), or a gas turbine/diesel engine combined with a "
        "GENERATOR_EFFICIENCY.",
    ),
]
