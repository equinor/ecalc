import enum
from typing import Annotated, Literal, TypeVar

from pydantic import Field

from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.components.yaml_expression_type import YamlExpressionType
from libecalc.presentation.yaml.yaml_types.models.yaml_compressor_chart import UnitsField, YamlCurve, YamlUnits
from libecalc.presentation.yaml.yaml_types.models.yaml_compressor_stages import YamlControlMarginUnits
from libecalc.presentation.yaml.yaml_types.streams.yaml_inlet_stream import YamlInletStream
from libecalc.presentation.yaml.yaml_types.yaml_data_or_file import DataOrFile

StreamRef = str
PortName = str
PortReference = str  # hierarchical: "target.stage.port" or "stage.port" (single-target case)


class YamlPortType(enum.StrEnum):
    INLET = "INLET"


class YamlPort(YamlBase):
    type: Annotated[
        YamlPortType,
        Field(title="TYPE", description="Port direction. Currently only INLET is supported (stream enters the stage)."),
    ]


class YamlControlMargin(YamlBase):
    unit: YamlControlMarginUnits
    value: float


class YamlCompressorChart(YamlBase):
    curves: Annotated[
        DataOrFile[list[YamlCurve]],
        Field(description="Compressor chart curves, one per speed.", title="CURVES"),
    ]
    units: YamlUnits = UnitsField()


class YamlCompressorModelChart(YamlBase):
    type: Literal["COMPRESSOR_CHART"]
    chart: YamlCompressorChart
    control_margin: YamlControlMargin


ProcessUnitReference = str


class YamlCompressor(YamlBase):
    """
    A Compressor process unit
    """

    type: Literal["COMPRESSOR"]
    name: Annotated[
        ProcessUnitReference,
        Field(
            description="Name of the model. See documentation for more information.",
            title="NAME",
        ),
    ]
    compressor_model: YamlCompressorModelChart


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
    ports: Annotated[
        dict[PortName, YamlPort] | None,
        Field(
            title="PORTS",
            description=(
                "Optional mapping of port name → port specification. Declares physical interstage "
                "connection points where fluid streams can enter the stage."
            ),
        ),
    ] = None


TTarget = TypeVar("TTarget")


class YamlItem[TTarget](YamlBase):
    target: TTarget | ProcessSystemReference


class YamlSerialProcessSystem(YamlBase):
    type: Literal["SERIAL"]
    name: ProcessSystemReference
    items: list[YamlItem[YamlCompressorStageProcessSystem]]


class YamlRateDistributionEntry(YamlBase):
    port: Annotated[
        PortReference,
        Field(
            title="PORT",
            description="Hierarchical reference to a port: 'target.stage.port'. The 'target.' prefix may be omitted when the simulation has a single target.",
        ),
    ]
    rate_fraction: Annotated[
        float,
        Field(
            title="RATE_FRACTION",
            description="Fraction of the source stream's rate routed to this port. Fractions across all entries in a RATE_DISTRIBUTION must sum to 1.0.",
        ),
    ]


class YamlOverflow(YamlBase):
    from_reference: ProcessSystemReference
    to_reference: ProcessSystemReference


class YamlPortOverflow(YamlBase):
    from_reference: Annotated[
        PortReference,
        Field(
            title="FROM_REFERENCE",
            description="Source port from which excess rate is redirected when its capacity is exceeded.",
        ),
    ]
    to_reference: Annotated[
        PortReference,
        Field(
            title="TO_REFERENCE",
            description="Destination port that receives the redirected excess rate.",
        ),
    ]


class YamlIndividualStreamConnection(YamlBase):
    type: Literal["INDIVIDUAL_STREAM"]
    stream: Annotated[
        StreamRef,
        Field(
            title="STREAM",
            description="Reference to a stream declared in INLET_STREAMS. The full stream is routed to the specified port.",
        ),
    ]
    port: Annotated[
        PortReference,
        Field(
            title="PORT",
            description="Hierarchical reference to a port that receives the stream: 'target.stage.port'. The 'target.' prefix may be omitted when the simulation has a single target.",
        ),
    ]


class YamlCommonStreamConnection(YamlBase):
    type: Literal["COMMON_STREAM"]
    stream: Annotated[
        StreamRef,
        Field(
            title="STREAM",
            description="Reference to a stream declared in INLET_STREAMS. The stream is distributed across the ports listed in RATE_DISTRIBUTION.",
        ),
    ]
    rate_distribution: Annotated[
        list[YamlRateDistributionEntry],
        Field(
            title="RATE_DISTRIBUTION",
            description="Distribution of the source stream across one or more destination ports. Each entry specifies a port and the fraction of the stream's rate routed to it.",
        ),
    ]
    overflow: Annotated[
        list[YamlPortOverflow] | None,
        Field(
            title="OVERFLOW",
            description="Optional rules for redirecting excess rate between ports when a destination's capacity is exceeded.",
        ),
    ] = None


YamlConnection = Annotated[
    YamlIndividualStreamConnection | YamlCommonStreamConnection,
    Field(discriminator="type"),
]


class YamlStreamDistributionPriority(YamlBase):
    connections: Annotated[
        list[YamlConnection],
        Field(
            title="CONNECTIONS",
            description="Set of stream connections that together make up one complete stream-distribution configuration. Each entry routes one stream to one or more ports.",
        ),
    ]


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
        list[YamlItem[YamlSerialProcessSystem]],
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


YamlProcessUnit = Annotated[
    YamlCompressor,
    Field(discriminator="type"),
]

YamlProcessSystem = Annotated[
    YamlSerialProcessSystem | YamlCompressorStageProcessSystem,
    Field(discriminator="type"),
]
