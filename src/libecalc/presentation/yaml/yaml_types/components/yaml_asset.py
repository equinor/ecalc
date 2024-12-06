from pydantic import ConfigDict, Field, model_validator
from pydantic_core.core_schema import ValidationInfo

from libecalc.common.string.string_utils import get_duplicates
from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.components.system.yaml_consumer_system import YamlConsumerSystem
from libecalc.presentation.yaml.yaml_types.components.yaml_installation import (
    YamlInstallation,
)
from libecalc.presentation.yaml.yaml_types.facility_model.yaml_facility_model import (
    YamlFacilityModel,
)
from libecalc.presentation.yaml.yaml_types.fuel_type.yaml_fuel_type import YamlFuelType
from libecalc.presentation.yaml.yaml_types.models import YamlConsumerModel
from libecalc.presentation.yaml.yaml_types.time_series.yaml_time_series import (
    YamlTimeSeriesCollection,
)
from libecalc.presentation.yaml.yaml_types.yaml_default_datetime import (
    YamlDefaultDatetime,
)
from libecalc.presentation.yaml.yaml_types.yaml_variable import YamlVariables
from libecalc.presentation.yaml.yaml_validation_context import YamlModelValidationContextNames


class YamlAsset(YamlBase):
    """An eCalc™ yaml file"""

    model_config = ConfigDict(
        title="Asset",
    )

    time_series: list[YamlTimeSeriesCollection] = Field(
        None,
        title="TIME_SERIES",
        description="Defines the inputs for time dependent variables, or 'reservoir variables'."
        "\n\n$ECALC_DOCS_KEYWORDS_URL/TIME_SERIES",
    )
    facility_inputs: list[YamlFacilityModel] = Field(
        None,
        title="FACILITY_INPUTS",
        description="Defines input files which characterize various facility elements."
        "\n\n$ECALC_DOCS_KEYWORDS_URL/FACILITY_INPUTS",
    )
    models: list[YamlConsumerModel] = Field(
        None,
        title="MODELS",
        description="Defines input files which characterize various facility elements."
        "\n\n$ECALC_DOCS_KEYWORDS_URL/MODELS",
    )
    fuel_types: list[YamlFuelType] = Field(
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
    installations: list[YamlInstallation] = Field(
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

    @model_validator(mode="after")
    def validate_unique_component_names(self, info: ValidationInfo):
        """Ensure unique component names in model."""
        context = info.context
        if not context:
            return self

        if not context.get(YamlModelValidationContextNames.model_name):
            return self

        names = [context.get(YamlModelValidationContextNames.model_name)]

        for installation in self.installations:
            names.append(installation.name)
            for fuel_consumer in installation.fuel_consumers or []:
                names.append(fuel_consumer.name)
                if isinstance(fuel_consumer, YamlConsumerSystem):
                    for consumer in fuel_consumer.consumers:
                        names.append(consumer.name)

            for generator_set in installation.generator_sets or []:
                names.append(generator_set.name)
                for electricity_consumer in generator_set.consumers:
                    names.append(electricity_consumer.name)
                    if isinstance(electricity_consumer, YamlConsumerSystem):
                        for consumer in electricity_consumer.consumers:
                            names.append(consumer.name)

            for venting_emitter in installation.venting_emitters or []:
                names.append(venting_emitter.name)

        duplicated_names = get_duplicates(names)

        if len(duplicated_names) > 0:
            raise ValueError(
                "Component names must be unique. Components include the main model, installations,"
                " generator sets, electricity consumers, fuel consumers, systems and its consumers and direct emitters."
                f" Duplicated names are: {', '.join(duplicated_names)}"
            )

        return self

    @model_validator(mode="after")
    def validate_unique_fuel_names(self):
        fuel_names = []

        for fuel_type in self.fuel_types:
            fuel_names.append(fuel_type.name)

        duplicated_fuel_names = get_duplicates(fuel_names)
        if len(duplicated_fuel_names) > 0:
            raise ValueError(
                "Fuel type names must be unique." f" Duplicated names are: {', '.join(duplicated_fuel_names)}"
            )
        return self
