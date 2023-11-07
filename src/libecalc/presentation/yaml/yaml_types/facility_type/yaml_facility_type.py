from typing import Literal, Union

from pydantic import Field
from typing_extensions import Annotated

from libecalc.presentation.yaml.yaml_types import YamlBase


def FacilityTypeField():
    return Field(
        ...,
        title="TYPE",
        description="Defines the type of model applied on the data in the file.\n\n$ECALC_DOCS_KEYWORDS_URL/TYPE",
    )


class YamlFacilityAdjustment(YamlBase):
    constant: float = Field(
        0,
        title="CONSTANT",
        description="Adjust input data with a constant value.\n\n$ECALC_DOCS_KEYWORDS_URL/CONSTANT",
    )
    factor: float = Field(
        1,
        title="FACTOR",
        description="Adjust input data with a constant multiplier.\n\n$ECALC_DOCS_KEYWORDS_URL/FACTOR",
    )


class YamlFacilityTypeBase(YamlBase):
    name: str = Field(
        ...,
        title="NAME",
        description="Name of the facility input.\n\n$ECALC_DOCS_KEYWORDS_URL/NAME",
    )
    file: str = Field(
        ...,
        title="FILE",
        description="Specifies the name of an input file.\n\n$ECALC_DOCS_KEYWORDS_URL/FILE",
    )
    adjustment: YamlFacilityAdjustment = Field(
        None,
        title="ADJUSTMENT",
        description="Definition of adjustments to correct for mismatches in facility energy usage.\n\n$ECALC_DOCS_KEYWORDS_URL/ADJUSTMENT",
    )


class YamlGeneratorSetModel(YamlFacilityTypeBase):
    type: Literal["ELECTRICITY2FUEL"] = FacilityTypeField()


class YamlTabularModel(YamlFacilityTypeBase):
    type: Literal["TABULAR"] = FacilityTypeField()


class YamlCompressorTabularModel(YamlFacilityTypeBase):
    type: Literal["COMPRESSOR_TABULAR"] = FacilityTypeField()


class YamlPumpChartUnits(YamlBase):
    rate: Literal["AM3_PER_HOUR"] = Field(
        ...,
        title="RATE",
        description="Unit for rate in pump chart. Currently only AM3_PER_HOUR is supported",
    )
    head: Literal["M", "KJ_PER_KG", "JOULE_PER_KG"] = Field(
        ...,
        title="HEAD",
        description="Unit for head in pump chart. Supported units are M (default), KJ_PER_KG and JOULE_PER_KG",
    )
    efficiency: Literal["PERCENTAGE", "FRACTION"] = Field(
        ...,
        title="EFFICIENCY",
        description="Unit of efficiency in pump chart. Supported units are PERCENTAGE (default) and FRACTION.",
    )


class YamlPumpChartBase(YamlFacilityTypeBase):
    head_margin: float = Field(
        None,
        title="HEAD_MARGIN",
        description="Adjustment of the head margin for power calibration.\n\n$ECALC_DOCS_KEYWORDS_URL/HEAD_MARGIN",
    )
    units: YamlPumpChartUnits = Field(
        ..., title="UNITS", description="Units for pump charts: RATE, HEAD and EFFICIENCY."
    )


class YamlPumpChartSingleSpeed(YamlPumpChartBase):
    type: Literal["PUMP_CHART_SINGLE_SPEED"] = FacilityTypeField()


class YamlPumpChartVariableSpeed(YamlPumpChartBase):
    type: Literal["PUMP_CHART_VARIABLE_SPEED"] = FacilityTypeField()


YamlFacilityType = Annotated[
    Union[
        YamlGeneratorSetModel,
        YamlTabularModel,
        YamlCompressorTabularModel,
        YamlPumpChartSingleSpeed,
        YamlPumpChartVariableSpeed,
    ],
    Field(discriminator="type"),
]
