from typing import Annotated, Generic, Literal, TypeAlias, TypeVar

from pydantic import Field

from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.components.yaml_expression_type import YamlExpressionType
from libecalc.presentation.yaml.yaml_types.models.yaml_compressor_chart import UnitsField, YamlCurve, YamlUnits
from libecalc.presentation.yaml.yaml_types.models.yaml_compressor_stages import YamlControlMarginUnits
from libecalc.presentation.yaml.yaml_types.streams.yaml_inlet_stream import YamlInletStream
from libecalc.presentation.yaml.yaml_types.yaml_data_or_file import DataOrFile

StreamRef = str


class YamlControlMargin(YamlBase):
    unit: YamlControlMarginUnits
    value: float


class YamlCompressorChart(YamlBase):
    curves: DataOrFile[list[YamlCurve]] = Field(
        ..., description="Compressor chart curves, one per speed.", title="CURVES"
    )
    units: YamlUnits = UnitsField()


class YamlCompressorModelChart(YamlBase):
    type: Literal["COMPRESSOR_CHART"]
    chart: YamlCompressorChart
    control_margin: YamlControlMargin


YamlCompressorModel = YamlCompressorModelChart  # Could add compressor_sampled as a model if needed


ProcessUnitReference = str


class YamlCompressor(YamlBase):
    """
    A Compressor process unit
    """

    type: Literal["COMPRESSOR"]
    name: ProcessUnitReference = Field(
        ...,
        description="Name of the model. See documentation for more information.",
        title="NAME",
    )
    compressor_model: YamlCompressorModel


ProcessSystemReference: TypeAlias = str  # TODO: validate correct reference

CompressorReference = ProcessUnitReference  # TODO: validate correct process unit type


class YamlCompressorStageProcessSystem(YamlBase):
    type: Literal["COMPRESSOR_STAGE"]
    name: ProcessSystemReference
    inlet_temperature: YamlExpressionType = Field(
        ...,
        description="Inlet temperature in Celsius for stage",
        title="INLET_TEMPERATURE",
    )
    pressure_drop_ahead_of_stage: YamlExpressionType = Field(
        0.0,
        description="Pressure drop before compression stage [in bar]",
        title="PRESSURE_DROP_AHEAD_OF_STAGE",
    )
    compressor: CompressorReference | YamlCompressor


TTarget = TypeVar("TTarget")


class YamlItem(YamlBase, Generic[TTarget]):
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
    outlet_pressure: YamlExpressionType | None = Field(
        None,
        title="OUTLET_PRESSURE",
        description="Target outlet pressure [bara].",
    )


class YamlProcessSimulation(YamlBase):
    name: str
    targets: list[YamlItem[YamlSerialProcessSystem]] = Field(..., title="TARGETS")
    stream_distribution: YamlStreamDistribution
    constraints: dict[ProcessSystemReference, YamlProcessConstraints] = Field(
        default_factory=dict,
        title="CONSTRAINTS",
        description="Optional constraints per process system reference.",
    )


YamlProcessUnit = Annotated[
    YamlCompressor,
    Field(discriminator="type"),
]

YamlProcessSystem = Annotated[
    YamlSerialProcessSystem | YamlCompressorStageProcessSystem,
    Field(discriminator="type"),
]
