from pydantic import ConfigDict, Field, field_validator, model_validator
from pydantic_core.core_schema import ValidationInfo

from libecalc.common.string.string_utils import get_duplicates
from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.components.yaml_installation import YamlInstallation
from libecalc.presentation.yaml.yaml_types.facility_model.yaml_facility_model import YamlFacilityModel
from libecalc.presentation.yaml.yaml_types.fuel_type.yaml_fuel_type import YamlFuelType
from libecalc.presentation.yaml.yaml_types.models import YamlConsumerModel, YamlFluidModel
from libecalc.presentation.yaml.yaml_types.time_series.yaml_time_series import YamlTimeSeriesCollection
from libecalc.presentation.yaml.yaml_types.yaml_default_datetime import YamlDefaultDatetime
from libecalc.presentation.yaml.yaml_types.yaml_variable import YamlVariables
from libecalc.presentation.yaml.yaml_types.yaml_version import DEFAULT_YAML_VERSION, YamlMajorVersion
from libecalc.presentation.yaml.yaml_validation_context import YamlModelValidationContextNames


class YamlAsset(YamlBase):
    """A legacy (yaml version 1) eCalc™ yaml file"""

    model_config = ConfigDict(
        title="Asset",
    )

    yaml_version: YamlMajorVersion = Field(
        DEFAULT_YAML_VERSION,
        title="YAML_VERSION",
        description=f"The eCalc YAML schema major version. Defaults to {DEFAULT_YAML_VERSION} if not specified.",
    )
    time_series: list[YamlTimeSeriesCollection] = Field(
        default_factory=list,
        title="TIME_SERIES",
        description="Defines the inputs for time dependent variables, or 'reservoir variables'."
        "\n\n$ECALC_DOCS_KEYWORDS_URL/TIME_SERIES",
    )
    facility_inputs: list[YamlFacilityModel] = Field(
        default_factory=list,
        title="FACILITY_INPUTS",
        description="Defines input files which characterize various facility elements."
        "\n\n$ECALC_DOCS_KEYWORDS_URL/FACILITY_INPUTS",
    )
    fluid_models: dict[str, YamlFluidModel] = Field(
        default_factory=dict,
        title="FLUID_MODELS",
        description="Defines fluid models that can be referenced by inlet streams.",
    )
    models: list[YamlConsumerModel] = Field(
        default_factory=list,
        title="MODELS",
        description="Defines input files which characterize various facility elements."
        "\n\n$ECALC_DOCS_KEYWORDS_URL/MODELS",
    )
    fuel_types: list[YamlFuelType] = Field(
        default_factory=list,
        title="FUEL_TYPES",
        description="Specifies the various fuel types and associated emissions used in the model."
        "\n\n$ECALC_DOCS_KEYWORDS_URL/FUEL_TYPES",
    )
    variables: YamlVariables = Field(
        default_factory=dict,
        title="VARIABLES",
        description="Defines variables used in an energy usage model by means of expressions or constants."
        "\n\n$ECALC_DOCS_KEYWORDS_URL/VARIABLES",
    )
    installations: list[YamlInstallation] = Field(
        default_factory=list,
        title="INSTALLATIONS",
        description="Description of the system of energy consumers.\n\n$ECALC_DOCS_KEYWORDS_URL/INSTALLATIONS",
    )
    start: YamlDefaultDatetime | None = Field(
        None,
        title="START",
        description="Global start date for eCalc calculations in <YYYY-MM-DD> format."
        "\n\n$ECALC_DOCS_KEYWORDS_URL/START",
    )
    end: YamlDefaultDatetime = Field(
        ...,
        title="END",
        description="Global end date for eCalc calculations in <YYYY-MM-DD> format.\n\n$ECALC_DOCS_KEYWORDS_URL/END",
    )

    @model_validator(mode="after")
    def validate_required_root_elements_present(self):
        missing = {"fuel_types", "installations"} - self.model_fields_set
        if not missing:
            return self

        aliases = sorted(YamlAsset.model_fields[field_name].alias or field_name.upper() for field_name in missing)
        raise ValueError(f"The following root elements are required for yaml version 1: {', '.join(aliases)}.")

    @model_validator(mode="after")
    def validate_unique_component_names(self, info: ValidationInfo):
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

            for generator_set in installation.generator_sets or []:
                names.append(generator_set.name)
                for electricity_consumer in generator_set.consumers:
                    names.append(electricity_consumer.name)

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

    @field_validator("time_series", mode="after")
    @classmethod
    def validate_unique_time_series_names(cls, collection, info: ValidationInfo):
        duplicated_names = get_duplicates(item.name for item in collection)
        if len(duplicated_names) > 0:
            raise ValueError(
                f"{cls.model_fields[info.field_name].alias if info.field_name is not None else 'Unknown field'} names must be unique."
                f" Duplicated names are: {', '.join(duplicated_names)}"
            )
        return collection

    @model_validator(mode="after")
    def validate_unique_references(self):
        references = [facility_input.name for facility_input in self.facility_inputs]
        references.extend(model.name for model in self.models)
        references.extend(fuel_type.name for fuel_type in self.fuel_types)
        references.extend(self.fluid_models.keys())

        duplicated_references = get_duplicates(references)

        if len(duplicated_references) > 0:
            raise ValueError(
                f"References/names must be unique across {YamlAsset.model_fields['facility_inputs'].alias}, {YamlAsset.model_fields['models'].alias} and {YamlAsset.model_fields['fuel_types'].alias}."
                f" Duplicated references are: {', '.join(duplicated_references)}"
            )
        return self
