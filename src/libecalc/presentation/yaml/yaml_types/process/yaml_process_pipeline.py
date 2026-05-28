from typing import Annotated, Literal, TypeVar

from pydantic import Field

from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.components.yaml_expression_type import YamlExpressionType
from libecalc.presentation.yaml.yaml_types.process.yaml_process_units import ProcessUnitReference, YamlCompressor

type ProcessPipelineReference = str  # TODO: validate correct reference

CompressorReference = ProcessUnitReference  # TODO: validate correct process unit type


class YamlCompressorStageProcessSystem(YamlBase):
    type: Literal["COMPRESSOR_STAGE"]
    name: ProcessPipelineReference
    inlet_temperature: Annotated[
        YamlExpressionType,
        Field(
            description="Inlet temperature in Celsius for stage",
            title="INLET_TEMPERATURE",
        ),
    ]
    pressure_drop_ahead_of_stage: Annotated[
        YamlExpressionType,
        Field(
            description="Pressure drop before compression stage [in bar]",
            title="PRESSURE_DROP_AHEAD_OF_STAGE",
        ),
    ] = 0.0
    compressor: CompressorReference | YamlCompressor


TTarget = TypeVar("TTarget")


class YamlItem[TTarget](YamlBase):
    target: TTarget | ProcessPipelineReference


class YamlProcessPipeline(YamlBase):
    type: Literal["SERIAL"]
    name: ProcessPipelineReference
    items: list[YamlItem[YamlCompressorStageProcessSystem]]


YamlProcessSystem = Annotated[
    YamlProcessPipeline | YamlCompressorStageProcessSystem,
    Field(discriminator="type"),
]
