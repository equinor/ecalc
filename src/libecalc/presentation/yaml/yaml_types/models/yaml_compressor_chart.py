import enum
from typing import Annotated, Literal, Union

from pydantic import Field

from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.models.model_reference import ModelName
from libecalc.presentation.yaml.yaml_types.models.yaml_enums import (
    YamlChartType,
    YamlModelType,
)
from libecalc.presentation.yaml.yaml_types.yaml_data_or_file import DataOrFile


class YamlCurve(YamlBase):
    speed: float = 1
    rate: list[float]
    head: list[float]
    efficiency: list[float]


class YamlRateUnits(str, enum.Enum):
    AM3_PER_HOUR = "AM3_PER_HOUR"


class YamlHeadUnits(str, enum.Enum):
    M = "M"
    KJ_PER_KG = "KJ_PER_KG"
    JOULE_PER_KG = "JOULE_PER_KG"


class YamlEfficiencyUnits(str, enum.Enum):
    FRACTION = "FRACTION"
    PERCENTAGE = "PERCENTAGE"


class YamlUnits(YamlBase):
    rate: YamlRateUnits = Field(
        YamlRateUnits.AM3_PER_HOUR,
        description="Unit for rate in compressor chart. Currently only AM3_PER_HOUR is supported",
        title="RATE",
    )
    head: YamlHeadUnits = Field(
        YamlHeadUnits.M,
        description="Unit for head in compressor chart. Supported units are M, KJ_PER_KG, JOULE_PER_KG",
        title="HEAD",
    )
    efficiency: YamlEfficiencyUnits = Field(
        YamlEfficiencyUnits.PERCENTAGE,
        description="Unit of efficiency in compressor chart. Supported units are PERCENTAGE and FRACTION.",
        title="EFFICIENCY",
    )


def UnitsField() -> Field:
    return Field(default_factory=lambda: YamlUnits(), title="UNITS", description="Defines the units")


class YamlSingleSpeedChart(YamlBase):
    name: ModelName = Field(
        ...,
        description="Name of the model. See documentation for more information.",
        title="NAME",
    )
    type: Literal[YamlModelType.COMPRESSOR_CHART] = Field(
        YamlModelType.COMPRESSOR_CHART,
        description="Defines the type of model. See documentation for more information.",
        title="TYPE",
    )
    chart_type: Literal[YamlChartType.SINGLE_SPEED] = YamlChartType.SINGLE_SPEED
    curve: DataOrFile[YamlCurve] = Field(..., description="One single compressor chart curve.", title="CURVE")
    units: YamlUnits = UnitsField()


class YamlVariableSpeedChart(YamlBase):
    name: ModelName = Field(
        ...,
        description="Name of the model. See documentation for more information.",
        title="NAME",
    )
    type: Literal[YamlModelType.COMPRESSOR_CHART] = Field(
        YamlModelType.COMPRESSOR_CHART,
        description="Defines the type of model. See documentation for more information.",
        title="TYPE",
    )
    chart_type: Literal[YamlChartType.VARIABLE_SPEED] = YamlChartType.VARIABLE_SPEED
    curves: DataOrFile[list[YamlCurve]] = Field(
        ..., description="Compressor chart curves, one per speed.", title="CURVES"
    )
    units: YamlUnits = UnitsField()


class YamlGenericFromInputChart(YamlBase):
    name: ModelName = Field(
        ...,
        description="Name of the model. See documentation for more information.",
        title="NAME",
    )
    type: Literal[YamlModelType.COMPRESSOR_CHART] = Field(
        YamlModelType.COMPRESSOR_CHART,
        description="Defines the type of model. See documentation for more information.",
        title="TYPE",
    )
    chart_type: Literal[YamlChartType.GENERIC_FROM_INPUT] = YamlChartType.GENERIC_FROM_INPUT
    polytropic_efficiency: float = Field(
        ...,
        description="Polytropic efficiency for compressor chart",
        title="POLYTROPIC_EFFICIENCY",
    )
    units: YamlUnits = UnitsField()


class YamlGenericFromDesignPointChart(YamlBase):
    name: ModelName = Field(
        ...,
        description="Name of the model. See documentation for more information.",
        title="NAME",
    )
    type: Literal[YamlModelType.COMPRESSOR_CHART] = Field(
        YamlModelType.COMPRESSOR_CHART,
        description="Defines the type of model. See documentation for more information.",
        title="TYPE",
    )
    chart_type: Literal[YamlChartType.GENERIC_FROM_DESIGN_POINT] = YamlChartType.GENERIC_FROM_DESIGN_POINT
    polytropic_efficiency: float = Field(
        ...,
        description="Polytropic efficiency for compressor chart",
        title="POLYTROPIC_EFFICIENCY",
    )
    design_rate: float = Field(..., description="Design rate for generic compressor chart", title="DESIGN_RATE")
    design_head: float = Field(..., description="Design head for generic compressor chart", title="DESIGN_HEAD")
    units: YamlUnits


YamlCompressorChart = Annotated[
    Union[YamlSingleSpeedChart, YamlVariableSpeedChart, YamlGenericFromDesignPointChart, YamlGenericFromInputChart],
    Field(discriminator="chart_type"),
]
