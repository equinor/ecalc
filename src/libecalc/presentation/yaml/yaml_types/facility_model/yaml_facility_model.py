from typing import Annotated, Literal, Union

from pydantic import Field, field_validator

from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.facility_model.yaml_facility_model_type import YamlFacilityModelType
from libecalc.presentation.yaml.yaml_types.models.yaml_compressor_chart import UnitsField, YamlUnits
from libecalc.presentation.yaml.yaml_validators.file_validators import (
    file_exists_validator,
)


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


class YamlFacilityModelBase(YamlBase):
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

    validate_file_exists = field_validator("file", mode="after")(file_exists_validator)


class YamlGeneratorSetModel(YamlFacilityModelBase):
    type: Literal[YamlFacilityModelType.ELECTRICITY2FUEL] = FacilityTypeField()


class YamlTabularModel(YamlFacilityModelBase):
    type: Literal[YamlFacilityModelType.TABULAR] = FacilityTypeField()


class YamlCompressorTabularModel(YamlFacilityModelBase):
    type: Literal[YamlFacilityModelType.COMPRESSOR_TABULAR] = FacilityTypeField()


class YamlPumpChartBase(YamlFacilityModelBase):
    head_margin: float = Field(
        0.0,
        title="HEAD_MARGIN",
        description="Adjustment of the head margin for power calibration.\n\n$ECALC_DOCS_KEYWORDS_URL/HEAD_MARGIN",
    )
    units: YamlUnits = UnitsField()


class YamlPumpChartSingleSpeed(YamlPumpChartBase):
    type: Literal[YamlFacilityModelType.PUMP_CHART_SINGLE_SPEED] = FacilityTypeField()


class YamlPumpChartVariableSpeed(YamlPumpChartBase):
    type: Literal[YamlFacilityModelType.PUMP_CHART_VARIABLE_SPEED] = FacilityTypeField()


YamlFacilityModel = Annotated[
    Union[
        YamlGeneratorSetModel,
        YamlTabularModel,
        YamlCompressorTabularModel,
        YamlPumpChartSingleSpeed,
        YamlPumpChartVariableSpeed,
    ],
    Field(discriminator="type"),
]
