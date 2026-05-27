from typing import Annotated, Literal, TypeVar

from pydantic import Field

from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.components.yaml_expression_type import YamlExpressionType
from libecalc.presentation.yaml.yaml_types.components.yaml_process_units import (
    ProcessUnitReference,
    YamlCompressor,
)
from libecalc.presentation.yaml.yaml_types.streams.yaml_inlet_stream import YamlInletStream

StreamRef = str


type ProcessSystemReference = str  # TODO: validate correct reference

CompressorReference = ProcessUnitReference  # TODO: validate correct process unit type


class YamlCompressorStageProcessSystem(YamlBase):
    type: Literal["COMPRESSOR_STAGE"]
    name: ProcessSystemReference
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
    target: TTarget | ProcessSystemReference


class YamlProcessPipeline(YamlBase):
    type: Literal["SERIAL"]
    name: ProcessSystemReference
    items: list[YamlItem[YamlCompressorStageProcessSystem]]


class YamlOverflow(YamlBase):
    from_reference: ProcessSystemReference
    to_reference: ProcessSystemReference


class YamlCommonStreamSetting(YamlBase):
    rate_fractions: list[YamlExpressionType]
    overflow: list[YamlOverflow] | None = None


class YamlCommonStreamDistribution(YamlBase):
    method: Literal["COMMON_STREAM"]
    inlet_stream: StreamRef | YamlInletStream
    settings: list[YamlCommonStreamSetting]


class YamlIndividualStreamDistribution(YamlBase):
    method: Literal["INDIVIDUAL_STREAMS"]
    inlet_streams: list[StreamRef | YamlInletStream]


YamlStreamDistribution = Annotated[
    YamlCommonStreamDistribution | YamlIndividualStreamDistribution, Field(discriminator="method")
]


class YamlProcessConstraints(YamlBase):
    outlet_pressure: Annotated[
        YamlExpressionType,
        Field(
            title="OUTLET_PRESSURE",
            description="Target outlet pressure [bara].",
        ),
    ]


class YamlProcessSimulation(YamlBase):
    name: str
    targets: Annotated[
        list[YamlItem[YamlProcessPipeline]],
        Field(title="TARGETS"),
    ]
    stream_distribution: YamlStreamDistribution
    pressure_control: Annotated[
        dict[
            ProcessSystemReference,
            Literal[
                "COMMON_ASV", "INDIVIDUAL_ASV_RATE", "INDIVIDUAL_ASV_PRESSURE", "DOWNSTREAM_CHOKE", "UPSTREAM_CHOKE"
            ],
        ],
        Field(
            title="PRESSURE_CONTROLS",
            description="Pressure control strategy per target",
        ),
    ]
    constraints: Annotated[
        dict[ProcessSystemReference, YamlProcessConstraints],
        Field(
            title="CONSTRAINTS",
            description="Constraints per target.",
        ),
    ]


YamlProcessSystem = Annotated[
    YamlProcessPipeline | YamlCompressorStageProcessSystem,
    Field(discriminator="type"),
]
