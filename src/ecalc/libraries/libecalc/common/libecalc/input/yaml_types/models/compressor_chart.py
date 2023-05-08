import enum
import json
from pathlib import Path
from typing import List, Literal, Union

import pydantic
from libecalc.input.yaml_types import YamlBase
from libecalc.input.yaml_types.models.enums import ChartType, ModelType
from pydantic import Field
from typing_extensions import Annotated


class CurvesFile(YamlBase):
    file: Path = Field(
        ...,
        description="Specifies the name of an input file. See documentation for more information.",
        title="FILE",
    )

    def to_dto(self):
        raise NotImplementedError


class Curve(YamlBase):
    speed: float
    rate: List[float]
    head: List[float]
    efficiency: List[float]

    def to_dto(self):
        raise NotImplementedError


CurvesArray = List[Curve]

Curves = Union[CurvesArray, CurvesFile]


class RateUnits(enum.Enum):
    AM3_PER_HOUR = "AM3_PER_HOUR"


class HeadUnits(enum.Enum):
    M = "M"
    KJ_PER_KG = "KJ_PER_KG"
    JOULE_PER_KG = "JOULE_PER_KG"


class EfficiencyUnits(enum.Enum):
    FRACTION = "FRACTION"
    PERCENTAGE = "PERCENTAGE"


class Units(YamlBase):
    rate: RateUnits = Field(
        RateUnits.AM3_PER_HOUR,
        description="Unit for rate in compressor chart. Currently only AM3_PER_HOUR is supported",
        title="RATE",
    )
    head: HeadUnits = Field(
        HeadUnits.M,
        description="Unit for head in compressor chart. Supported units are M, KJ_PER_KG, JOULE_PER_KG",
        title="HEAD",
    )
    efficiency: EfficiencyUnits = Field(
        EfficiencyUnits.PERCENTAGE,
        description="Unit of efficiency in compressor chart. Supported units are PERCENTAGE and FRACTION.",
        title="EFFICIENCY",
    )

    def to_dto(self):
        raise NotImplementedError


class VariableSpeedChart(YamlBase):
    name: str = Field(
        ...,
        description="Name of the model. See documentation for more information.",
        title="NAME",
    )
    type: Literal[ModelType.COMPRESSOR_CHART] = Field(
        ModelType.COMPRESSOR_CHART,
        description="Defines the type of model. See documentation for more information.",
        title="TYPE",
    )
    chart_type: Literal[ChartType.VARIABLE_SPEED] = ChartType.VARIABLE_SPEED
    curves: Curves = Field(..., description="Compressor chart curves, one per speed.", title="CURVES")
    units: Units = None

    def to_dto(self):
        raise NotImplementedError


class GenericFromInputChart(YamlBase):
    name: str = Field(
        ...,
        description="Name of the model. See documentation for more information.",
        title="NAME",
    )
    type: Literal[ModelType.COMPRESSOR_CHART] = Field(
        ModelType.COMPRESSOR_CHART,
        description="Defines the type of model. See documentation for more information.",
        title="TYPE",
    )
    chart_type: Literal[ChartType.GENERIC_FROM_INPUT] = ChartType.GENERIC_FROM_INPUT
    polytropic_efficiency: float = Field(
        ...,
        description="Polytropic efficiency for compressor chart",
        title="POLYTROPIC_EFFICIENCY",
    )

    def to_dto(self):
        raise NotImplementedError


class GenericFromDesignPointChart(YamlBase):
    name: str = Field(
        ...,
        description="Name of the model. See documentation for more information.",
        title="NAME",
    )
    type: Literal[ModelType.COMPRESSOR_CHART] = Field(
        ModelType.COMPRESSOR_CHART,
        description="Defines the type of model. See documentation for more information.",
        title="TYPE",
    )
    chart_type: Literal[ChartType.GENERIC_FROM_DESIGN_POINT] = ChartType.GENERIC_FROM_DESIGN_POINT
    polytropic_efficiency: float = Field(
        ...,
        description="Polytropic efficiency for compressor chart",
        title="POLYTROPIC_EFFICIENCY",
    )
    design_rate: float = Field(..., description="Design rate for generic compressor chart", title="DESIGN_RATE")
    design_head: float = Field(..., description="Design head for generic compressor chart", title="DESIGN_HEAD")
    units: Units

    def to_dto(self):
        raise NotImplementedError


CompressorChart = Annotated[
    Union[VariableSpeedChart, GenericFromDesignPointChart, GenericFromInputChart],
    Field(discriminator="chart_type"),
]
if __name__ == "__main__":
    schema = pydantic.schema_of(CompressorChart)
    print(json.dumps(schema, indent=2))
