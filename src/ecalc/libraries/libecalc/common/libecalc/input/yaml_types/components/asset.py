from typing import List

from libecalc.input.yaml_types import YamlBase
from libecalc.input.yaml_types.components.installation import YamlInstallation
from libecalc.input.yaml_types.placeholder_type import PlaceholderType
from libecalc.input.yaml_types.variable import Variables
from pydantic import Field


class YamlAsset(YamlBase):
    """An eCalc™ yaml file"""

    class Config:
        title = "Asset"

    time_series: PlaceholderType = Field(
        None,
        title="TIME_SERIES",
        description="Defines the inputs for time dependent variables, or 'reservoir variables'."
        "\n\n$ECALC_DOCS_KEYWORDS_URL/TIME_SERIES",
    )
    facility_inputs: PlaceholderType = Field(
        None,
        title="FACILITY_INPUTS",
        description="Defines input files which characterize various facility elements."
        "\n\n$ECALC_DOCS_KEYWORDS_URL/FACILITY_INPUTS",
    )
    models: PlaceholderType = Field(
        None,
        title="MODELS",
        description="Defines input files which characterize various facility elements."
        "\n\n$ECALC_DOCS_KEYWORDS_URL/MODELS",
    )
    fuel_types: PlaceholderType = Field(
        None,
        title="FUEL_TYPES",
        description="Specifies the various fuel types and associated emissions used in the model."
        "\n\n$ECALC_DOCS_KEYWORDS_URL/FUEL_TYPES",
    )
    variables: Variables = Field(
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
    start: str = Field(
        None,  # TODO: DefaultDatetime?
        title="START",
        description="Global start date for eCalc calculations in <YYYY-MM-DD> format."
        "\n\n$ECALC_DOCS_KEYWORDS_URL/START",
    )
    end: str = Field(
        None,  # TODO: DefaultDatetime?
        title="END",
        description="Global end date for eCalc calculations in <YYYY-MM-DD> format." "\n\n$ECALC_DOCS_KEYWORDS_URL/END",
    )
