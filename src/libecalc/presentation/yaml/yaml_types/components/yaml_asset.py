from typing import List

from pydantic import ConfigDict, Field

from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.components.yaml_installation import (
    YamlInstallation,
)
from libecalc.presentation.yaml.yaml_types.facility_type.yaml_facility_type import (
    YamlFacilityType,
)
from libecalc.presentation.yaml.yaml_types.fuel_type.yaml_fuel_type import YamlFuelType
from libecalc.presentation.yaml.yaml_types.models import YamlModel
from libecalc.presentation.yaml.yaml_types.time_series.yaml_time_series import (
    YamlTimeSeriesCollection,
)
from libecalc.presentation.yaml.yaml_types.yaml_default_datetime import (
    YamlDefaultDatetime,
)
from libecalc.presentation.yaml.yaml_types.yaml_variable import YamlVariables


class YamlAsset(YamlBase):
    """An eCalc™ yaml file"""

    model_config = ConfigDict(
        title="Asset",
    )

    time_series: List[YamlTimeSeriesCollection] = Field(
        None,
        title="TIME_SERIES",
        description="Defines the inputs for time dependent variables, or 'reservoir variables'."
        "\n\n$ECALC_DOCS_KEYWORDS_URL/TIME_SERIES",
    )
    facility_inputs: List[YamlFacilityType] = Field(
        None,
        title="FACILITY_INPUTS",
        description="Defines input files which characterize various facility elements."
        "\n\n$ECALC_DOCS_KEYWORDS_URL/FACILITY_INPUTS",
    )
    models: List[YamlModel] = Field(
        None,
        title="MODELS",
        description="Defines input files which characterize various facility elements."
        "\n\n$ECALC_DOCS_KEYWORDS_URL/MODELS",
    )
    fuel_types: List[YamlFuelType] = Field(
        ...,
        title="FUEL_TYPES",
        description="Specifies the various fuel types and associated emissions used in the model."
        "\n\n$ECALC_DOCS_KEYWORDS_URL/FUEL_TYPES",
    )
    variables: YamlVariables = Field(
        None,
        title="VARIABLES",
        description="Defines variables used in an energy usage model by means of expressions or constants."
        "\n\n$ECALC_DOCS_KEYWORDS_URL/VARIABLES",
    )
    installations: List[YamlInstallation] = Field(
        ...,
        title="INSTALLATIONS",
        description="Description of the system of energy consumers." "\n\n$ECALC_DOCS_KEYWORDS_URL/INSTALLATIONS",
    )
    start: YamlDefaultDatetime = Field(
        None,
        title="START",
        description="Global start date for eCalc calculations in <YYYY-MM-DD> format."
        "\n\n$ECALC_DOCS_KEYWORDS_URL/START",
    )
    end: YamlDefaultDatetime = Field(
        None,
        title="END",
        description="Global end date for eCalc calculations in <YYYY-MM-DD> format." "\n\n$ECALC_DOCS_KEYWORDS_URL/END",
    )
