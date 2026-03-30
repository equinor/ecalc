from typing import Annotated, Literal, TypeAlias

from pydantic import Field

from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.components.yaml_expression_type import YamlExpressionType
from libecalc.presentation.yaml.yaml_types.models.yaml_compressor_chart import UnitsField, YamlCurve, YamlUnits
from libecalc.presentation.yaml.yaml_types.models.yaml_compressor_stages import YamlControlMarginUnits
from libecalc.presentation.yaml.yaml_types.models.yaml_enums import YamlAntiSurge, YamlPressureControl
from libecalc.presentation.yaml.yaml_types.streams.yaml_inlet_stream import YamlInletStream, YamlInletStreamRate
from libecalc.presentation.yaml.yaml_types.yaml_data_or_file import DataOrFile

StreamRef = str


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


ProcessSystemReference: TypeAlias = str  # TODO: validate correct reference

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
    compressor: CompressorReference | YamlCompressor


class YamlInterstagePressureDrop(YamlBase):
    type: Literal["PRESSURE_DROP"]
    name: ProcessSystemReference
    pressure_drop: Annotated[
        YamlExpressionType,
        Field(
            title="PRESSURE_DROP",
            description="Pressure drop across the choke [bar].",
        ),
    ]


class YamlInterstageMixer(YamlBase):
    type: Literal["MIXER"]
    name: ProcessSystemReference


class YamlInterstageSplitter(YamlBase):
    type: Literal["SPLITTER"]
    name: ProcessSystemReference


YamlInterstageItem = Annotated[
    YamlInterstagePressureDrop | YamlInterstageMixer | YamlInterstageSplitter,
    Field(discriminator="type"),
]


class YamlSerialProcessSystem(YamlBase):
    type: Literal["SERIAL"]
    name: ProcessSystemReference
    items: list[ProcessSystemReference]
    anti_surge: YamlAntiSurge = Field(
        default=YamlAntiSurge.INDIVIDUAL_ASV,
        title="ANTI_SURGE",
        description=(
            "Anti-surge strategy for the train. INDIVIDUAL_ASV means each compressor "
            "has its own recirculation valve. COMMON_ASV means a shared valve across the train. "
            "Defaults to INDIVIDUAL_ASV."
        ),
    )


YamlProcessUnit = Annotated[
    YamlCompressor,
    Field(discriminator="type"),
]

YamlProcessSystem = Annotated[
    YamlSerialProcessSystem
    | YamlCompressorStageProcessSystem
    | YamlInterstagePressureDrop
    | YamlInterstageSplitter
    | YamlInterstageMixer,
    Field(discriminator="type"),
]


class YamlSegmentConstraint(YamlBase):
    outlet_pressure: Annotated[
        YamlExpressionType,
        Field(
            title="OUTLET_PRESSURE",
            description="Target outlet pressure [bara].",
        ),
    ]
    pressure_control: Annotated[
        YamlPressureControl,
        Field(
            title="PRESSURE_CONTROL",
            description="Pressure control strategy for this segment.",
        ),
    ]


class YamlSimulationTarget(YamlBase):
    target: ProcessSystemReference
    constraints: dict[ProcessSystemReference, YamlSegmentConstraint] = Field(
        default_factory=dict,
        title="CONSTRAINTS",
        description=(
            "Constraints keyed by process system item name or the train name itself. "
            "Using the train name as a key targets the train outlet regardless of which stage is last."
        ),
    )
    mixer_streams: dict[ProcessSystemReference, StreamRef] = Field(
        default_factory=dict,
        title="MIXER_STREAMS",
        description="References to inlet streams for mixer items in this train, keyed by mixer name.",
    )
    splitter_rates: dict[ProcessSystemReference, YamlInletStreamRate] = Field(
        default_factory=dict,
        title="SPLITTER_RATES",
        description="Extraction rates for splitter items in this train, keyed by splitter name.",
    )


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


class YamlProcessSimulation(YamlBase):
    name: str
    targets: Annotated[list[YamlSimulationTarget], Field(title="TARGETS")]
    stream_distribution: YamlStreamDistribution
