from typing import Annotated, Literal

from pydantic import ConfigDict, Field

from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.process.yaml_process_references import (
    DefinitionReference,
    validate_definition_reference_or_inline_model,
)
from libecalc.presentation.yaml.yaml_types.process.yaml_process_units import YamlPressureDropperDefinition
from libecalc.presentation.yaml.yaml_types.pump.yaml_pump_model import YamlPumpModel
from libecalc.presentation.yaml.yaml_types.yaml_pump import PumpReference

PumpModelOrReference = Annotated[
    DefinitionReference | YamlPumpModel,
    validate_definition_reference_or_inline_model(YamlPumpModel),
]


class YamlPumpProcessUnit(YamlBase):
    """A pump from PUMPS, run with a pump model."""

    model_config = ConfigDict(title="PUMP_PROCESS_UNIT")

    type: Literal["PUMP"]
    pump: Annotated[
        PumpReference,
        Field(title="PUMP", description="Reference to a pump defined in PUMPS."),
    ]
    model: Annotated[
        PumpModelOrReference,
        Field(title="MODEL", description="The pump model, a reference to DEFINITIONS.PUMP_MODELS or inline."),
    ]


YamlPumpPipelineUnit = Annotated[
    YamlPumpProcessUnit | YamlPressureDropperDefinition,
    Field(discriminator="type"),
]


class YamlPumpPipeline(YamlBase):
    model_config = ConfigDict(title="PUMP_PIPELINE")

    name: Annotated[str, Field(title="NAME", description="Name of the pump pipeline.")]
    process_units: Annotated[
        list[YamlPumpPipelineUnit],
        Field(title="PROCESS_UNITS", description="The process units in flow order, each given by its TYPE."),
    ]
