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
    OUTLET = "OUTLET"


class YamlPort(YamlBase):
    type: Annotated[
        YamlPortType,
        Field(
            title="TYPE",
            description="Port direction: INLET (stream enters the stage) or OUTLET (stream leaves the stage).",
        ),
    ]


class YamlStreamConnection(YamlBase):
    port: Annotated[
        PortReference,
        Field(
            title="PORT",
            description=(
                "Hierarchical reference to a port declared on a stage: 'target.stage.port'. "
                "The 'target.' prefix may be omitted when the simulation has a single target."
            ),
        ),
    ]
    stream: Annotated[
        StreamRef,
        Field(
            title="STREAM",
            description="Reference to a stream declared in INLET_STREAMS.",
        ),
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
                "connection points where fluid streams can be added (INLET) or extracted (OUTLET). "
                "Wired to streams via STREAM_CONNECTIONS on the PROCESS_SIMULATION."
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
        list[YamlItem[YamlSerialProcessSystem]],
        Field(title="TARGETS"),
    ]
    stream_distribution: YamlStreamDistribution
    stream_connections: Annotated[
        list[YamlStreamConnection] | None,
        Field(
            title="STREAM_CONNECTIONS",
            description=(
                "Optional list of port-to-stream mappings. Each entry connects a port "
                "(declared on a stage via PORTS) to a stream (declared in INLET_STREAMS). "
                "INLET ports receive a stream into the train; OUTLET ports extract a stream."
            ),
        ),
    ] = None
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
