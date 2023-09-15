from typing import Any, Dict, List, Type

from libecalc.input.yaml_types import YamlBase
from libecalc.input.yaml_types.components.yaml_installation import YamlInstallation
from libecalc.input.yaml_types.yaml_placeholder_type import YamlPlaceholderType
from libecalc.input.yaml_types.yaml_schema_helpers import (
    replace_placeholder_property_with_legacy_ref,
)
from libecalc.input.yaml_types.yaml_variable import YamlVariables
from pydantic import Field


class YamlAsset(YamlBase):
    """An eCalc™ yaml file"""

    class Config:
        title = "Asset"

        @staticmethod
        def schema_extra(schema: Dict[str, Any], model: Type["YamlInstallation"]) -> None:
            replace_placeholder_property_with_legacy_ref(
                schema=schema,
                property_key="TIME_SERIES",
                property_ref="$SERVER_NAME/api/v1/schema-validation/time-series.json#properties/TIME_SERIES",
            )
            replace_placeholder_property_with_legacy_ref(
                schema=schema,
                property_key="FACILITY_INPUTS",
                property_ref="$SERVER_NAME/api/v1/schema-validation/facility-files.json#properties/FACILITY_INPUTS",
            )
            replace_placeholder_property_with_legacy_ref(
                schema=schema,
                property_key="MODELS",
                property_ref="$SERVER_NAME/api/v1/schema-validation/models.json#properties/MODELS",
            )
            replace_placeholder_property_with_legacy_ref(
                schema=schema,
                property_key="FUEL_TYPES",
                property_ref="$SERVER_NAME/api/v1/schema-validation/fuel-types.json#properties/FUEL_TYPES",
            )

    time_series: YamlPlaceholderType = Field(
        None,
        title="TIME_SERIES",
        description="Defines the inputs for time dependent variables, or 'reservoir variables'."
        "\n\n$ECALC_DOCS_KEYWORDS_URL/TIME_SERIES",
    )
    facility_inputs: YamlPlaceholderType = Field(
        None,
        title="FACILITY_INPUTS",
        description="Defines input files which characterize various facility elements."
        "\n\n$ECALC_DOCS_KEYWORDS_URL/FACILITY_INPUTS",
    )
    models: YamlPlaceholderType = Field(
        None,
        title="MODELS",
        description="Defines input files which characterize various facility elements."
        "\n\n$ECALC_DOCS_KEYWORDS_URL/MODELS",
    )
    fuel_types: YamlPlaceholderType = Field(
        None,
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