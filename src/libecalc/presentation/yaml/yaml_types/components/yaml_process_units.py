from typing import Annotated, Literal

from pydantic import Field

from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.components.yaml_expression_type import YamlExpressionType
from libecalc.presentation.yaml.yaml_types.models.yaml_compressor_chart import UnitsField, YamlCurve, YamlUnits
from libecalc.presentation.yaml.yaml_types.models.yaml_compressor_stages import YamlControlMarginUnits
from libecalc.presentation.yaml.yaml_types.yaml_data_or_file import DataOrFile

ProcessUnitReference = str


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


class YamlPressureDropper(YamlBase):
    """A pressure dropper unit — reduces stream pressure by a fixed amount."""

    type: Literal["PRESSURE_DROPPER"]
    pressure_drop: Annotated[
        YamlExpressionType,
        Field(
            description="Pressure drop across the unit [bar].",
            title="PRESSURE_DROP",
        ),
    ]


class YamlTemperatureSetter(YamlBase):
    """A temperature setter unit — forces the stream to a specified temperature."""

    type: Literal["TEMPERATURE_SETTER"]
    temperature: Annotated[
        YamlExpressionType,
        Field(
            description="Target temperature [Celsius].",
            title="TEMPERATURE",
        ),
    ]


class YamlLiquidRemover(YamlBase):
    """A liquid remover (scrubber) unit — removes any condensed liquid from
    the stream, leaving only the gas phase.

    No-op if the stream is already pure vapor.
    """

    type: Literal["LIQUID_REMOVER"]


YamlProcessUnit = Annotated[
    YamlCompressor | YamlPressureDropper | YamlTemperatureSetter | YamlLiquidRemover,
    Field(discriminator="type"),
]
