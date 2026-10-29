from collections import defaultdict

from pydantic import ConfigDict, Field, field_validator, model_validator
from pydantic_core.core_schema import ValidationInfo

from libecalc.common.string.string_utils import get_duplicates
from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.components.yaml_installation import YamlInstallation
from libecalc.presentation.yaml.yaml_types.energy.yaml_energy_network import (
    YamlDriveTrain,
    YamlEnergyNetwork,
)
from libecalc.presentation.yaml.yaml_types.energy.yaml_generator_definition import YamlGeneratorDefinition
from libecalc.presentation.yaml.yaml_types.energy.yaml_turbine_definition import YamlTurbineDefinition
from libecalc.presentation.yaml.yaml_types.facility_model.yaml_facility_model import YamlFacilityModel
from libecalc.presentation.yaml.yaml_types.fuel_type.yaml_fuel_type import YamlFuelType
from libecalc.presentation.yaml.yaml_types.models import YamlConsumerModel, YamlFluidModel
from libecalc.presentation.yaml.yaml_types.process.yaml_fluid_definitions import YamlFluidDefinition
from libecalc.presentation.yaml.yaml_types.process.yaml_process_pipeline import (
    YamlCompressorProcessUnitInstance,
    YamlProcessPipeline,
)
from libecalc.presentation.yaml.yaml_types.process.yaml_process_simulation import (
    YamlEcalcEvent,
    YamlProcessEvent,
    YamlProcessSimulation,
    YamlPumpProcessSimulation,
)
from libecalc.presentation.yaml.yaml_types.process.yaml_process_units import (
    YamlReferenceableProcessUnitDefinition,
)
from libecalc.presentation.yaml.yaml_types.streams.yaml_inlet_stream import YamlInletStream
from libecalc.presentation.yaml.yaml_types.time_series.yaml_time_series import YamlTimeSeriesCollection
from libecalc.presentation.yaml.yaml_types.yaml_default_datetime import YamlDefaultDatetime
from libecalc.presentation.yaml.yaml_types.yaml_shaft import ShaftReference, YamlShaft
from libecalc.presentation.yaml.yaml_types.yaml_variable import YamlVariables
from libecalc.presentation.yaml.yaml_types.yaml_version import (
    DEFAULT_YAML_VERSION,
    V2,
    YamlMajorVersion,
    get_unavailable_field_names,
    version_field_json_schema_extra,
    yaml_element_lifecycle,
)
from libecalc.presentation.yaml.yaml_validation_context import YamlModelValidationContextNames


class YamlDefinitions(YamlBase):
    """Definitions section of an eCalc™ yaml file, containing reusable definitions."""

    model_config = ConfigDict(
        title="Definitions",
    )

    process_units: dict[str, YamlReferenceableProcessUnitDefinition] = Field(
        default_factory=dict,
        title="PROCESS_UNITS",
        description="Defines process units used in PROCESS_PIPELINES.",
    )

    fluids: dict[str, YamlFluidDefinition] = Field(
        default_factory=dict,
        title="FLUIDS",
        description="Defines fluids that can be referenced in inlet streams.",
    )

    turbines: dict[str, YamlTurbineDefinition] = Field(
        default_factory=dict,
        title="TURBINES",
        description="Defines gas turbines that can be referenced from GAS_TURBINE units in the ENERGY_NETWORK. "
        "Fuel follows the efficiency curve: demand below the first LOAD burns the fuel of the first LOAD, and the "
        "last efficiency is used above the last LOAD. The last LOAD is the maximum power, which is the capacity of "
        "a GAS_TURBINE.",
    )

    generators: dict[str, YamlGeneratorDefinition] = Field(
        default_factory=dict,
        title="GENERATORS",
        description="Defines generators that can be referenced from GENERATOR units in the ENERGY_NETWORK. "
        "Fuel is interpolated from the POWER/FUEL curve. Below the first POWER the lowest FUEL is used, and above "
        "the last POWER the highest FUEL is used. The last POWER is the maximum power, which is the capacity of a "
        "GENERATOR.",
    )


class YamlAsset(YamlBase):
    """An eCalc™ yaml file"""

    model_config = ConfigDict(
        title="Asset",
    )

    yaml_version: YamlMajorVersion = Field(
        DEFAULT_YAML_VERSION,
        title="YAML_VERSION",
        description="The eCalc YAML schema major version. Determines which root elements are available. "
        "Only the major version is tracked, e.g. YAML_VERSION: 2 allows any 2.x.y root elements. "
        f"Defaults to {DEFAULT_YAML_VERSION} if not specified.",
        json_schema_extra=version_field_json_schema_extra(DEFAULT_YAML_VERSION),
    )
    definitions: YamlDefinitions = Field(
        default_factory=YamlDefinitions,
        title="DEFINITIONS",
        description="Contains reusable definitions.",
        json_schema_extra=yaml_element_lifecycle(available_since=V2),
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
        json_schema_extra=yaml_element_lifecycle(deprecated_since=V2),
    )
    inlet_streams: dict[str, YamlInletStream] = Field(
        default_factory=dict,
        title="INLET_STREAMS",
        description="Defines inlet streams that can be referenced by process system and stream distribution.",
        json_schema_extra=yaml_element_lifecycle(available_since=V2),
    )
    models: list[YamlConsumerModel] = Field(
        default_factory=list,
        title="MODELS",
        description="Defines input files which characterize various facility elements."
        "\n\n$ECALC_DOCS_KEYWORDS_URL/MODELS",
        json_schema_extra=yaml_element_lifecycle(deprecated_since=V2),
    )
    fuel_types: list[YamlFuelType] = Field(
        ...,
        title="FUEL_TYPES",
        description="Specifies the various fuel types and associated emissions used in the model."
        "\n\n$ECALC_DOCS_KEYWORDS_URL/FUEL_TYPES",
        json_schema_extra=yaml_element_lifecycle(deprecated_since=V2),
    )
    variables: YamlVariables = Field(
        default_factory=dict,
        title="VARIABLES",
        description="Defines variables used in an energy usage model by means of expressions or constants."
        "\n\n$ECALC_DOCS_KEYWORDS_URL/VARIABLES",
    )
    shafts: list[YamlShaft] = Field(
        default_factory=list,
        title="SHAFTS",
        description="Defines named shafts representing mechanical connections between drivers and driven equipment.",
        json_schema_extra=yaml_element_lifecycle(available_since=V2),
    )
    process_pipelines: dict[str, YamlProcessPipeline] = Field(
        default_factory=dict,
        title="PROCESS_PIPELINES",
        description="Defines process pipelines to use in process simulations.",
        json_schema_extra=yaml_element_lifecycle(available_since=V2),
    )
    process_simulations: list[YamlProcessSimulation] = Field(
        default_factory=list,
        title="PROCESS_SIMULATIONS",
        description="Defines one or more process simulations to be run.",
        json_schema_extra=yaml_element_lifecycle(available_since=V2),
    )
    ecalc_events: list[YamlEcalcEvent] = Field(
        default_factory=list,
        title="ECALC_EVENTS",
        description="Defines eCalc events associated with temporal model changes",
        json_schema_extra=yaml_element_lifecycle(available_since=V2),
    )
    energy_network: YamlEnergyNetwork | None = Field(
        None,
        title="ENERGY_NETWORK",
        description="Defines the energy network configuration.",
        json_schema_extra=yaml_element_lifecycle(available_since=V2),
    )
    process_events: list[YamlProcessEvent] = Field(
        default_factory=list,
        title="PROCESS_EVENTS",
        description="Defines process-specific events that reference global eCalc events.",
        json_schema_extra=yaml_element_lifecycle(available_since=V2),
    )
    pump_process_simulations: list[YamlPumpProcessSimulation] = Field(
        default_factory=list,
        title="PUMP_PROCESS_SIMULATIONS",
        description="Defines one or more liquid pump process simulations to be run.",
        json_schema_extra=yaml_element_lifecycle(available_since=V2),
    )
    installations: list[YamlInstallation] = Field(
        ...,
        title="INSTALLATIONS",
        description="Description of the system of energy consumers.\n\n$ECALC_DOCS_KEYWORDS_URL/INSTALLATIONS",
        json_schema_extra=yaml_element_lifecycle(deprecated_since=V2),
    )
    start: YamlDefaultDatetime = Field(
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
    def validate_root_elements_available_for_version(self):
        """Ensure root elements explicitly set in the yaml are available for the declared YAML_VERSION."""
        unavailable = get_unavailable_field_names(type(self), self.yaml_version, self.model_fields_set)
        if not unavailable:
            return self

        aliases = sorted(YamlAsset.model_fields[field_name].alias or field_name.upper() for field_name in unavailable)
        raise ValueError(
            f"The following root elements are not available for yaml version {self.yaml_version}: {', '.join(aliases)}."
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

    @model_validator(mode="after")
    def validate_pipeline_targeted_by_single_simulation(self):
        """A process pipeline can currently only be solved by a single process simulation."""
        simulations_by_target: dict[str, list[str]] = defaultdict(list)
        for process_simulation in self.process_simulations:
            for target in process_simulation.targets:
                simulations_by_target[target].append(process_simulation.name)

        conflicts = {
            target: simulation_names
            for target, simulation_names in simulations_by_target.items()
            if len(simulation_names) > 1
        }

        if conflicts:
            conflict_descriptions = ", ".join(
                f"'{target}' is targeted by {simulation_names}" for target, simulation_names in conflicts.items()
            )
            raise ValueError(
                "A process pipeline can currently only be targeted by one process simulation. "
                f"Conflicts found: {conflict_descriptions}."
            )

        return self

    @field_validator("time_series", mode="after")
    @classmethod
    def validate_unique_time_series_names(cls, collection, info: ValidationInfo):
        names = []

        for item in collection:
            names.append(item.name)

        duplicated_names = get_duplicates(names)
        if len(duplicated_names) > 0:
            raise ValueError(
                f"{cls.model_fields[info.field_name].alias if info.field_name is not None else 'Unknown field'} names must be unique."
                f" Duplicated names are: {', '.join(duplicated_names)}"
            )
        return collection

    @field_validator("shafts", mode="after")
    @classmethod
    def validate_unique_shaft_names(cls, shafts: list[YamlShaft], info: ValidationInfo) -> list[YamlShaft]:
        duplicated_names = get_duplicates(shaft.name for shaft in shafts)
        if duplicated_names:
            field_name = info.field_name
            alias = cls.model_fields[field_name].alias if field_name is not None else "SHAFTS"
            raise ValueError(
                f"{alias} names must be unique. Duplicated names are: {', '.join(sorted(duplicated_names))}"
            )
        return shafts

    @model_validator(mode="after")
    def validate_unique_references(self):
        references = []

        for facility_input in self.facility_inputs:
            references.append(facility_input.name)

        for model in self.models:
            references.append(model.name)

        for fuel_type in self.fuel_types:
            references.append(fuel_type.name)

        references.extend(self.process_pipelines.keys())

        references.extend(self.definitions.process_units.keys())
        references.extend(self.definitions.fluids.keys())
        references.extend(self.definitions.turbines.keys())
        references.extend(self.definitions.generators.keys())

        for process_simulation in self.process_simulations:
            references.append(process_simulation.name)

        for pump_process_simulation in self.pump_process_simulations:
            references.append(pump_process_simulation.name)

        # TODO: Add ecalc events references?

        references.extend(self.fluid_models.keys())

        references.extend(self.inlet_streams.keys())

        duplicated_references = get_duplicates(references)

        if len(duplicated_references) > 0:
            raise ValueError(
                f"References/names must be unique across {YamlAsset.model_fields['facility_inputs'].alias}, {YamlAsset.model_fields['models'].alias} and {YamlAsset.model_fields['fuel_types'].alias}."
                f" Duplicated references are: {', '.join(duplicated_references)}"
            )
        return self

    @model_validator(mode="after")
    def validate_process_pipeline_shaft_references(self):
        available_shaft_names = {shaft.name for shaft in self.shafts}

        for pipeline_name, pipeline in self.process_pipelines.items():
            for process_unit in pipeline.process_units:
                if not isinstance(process_unit, YamlCompressorProcessUnitInstance):
                    continue
                if process_unit.shaft not in available_shaft_names:
                    available = ", ".join(sorted(available_shaft_names)) or "none"
                    raise ValueError(
                        f"Process unit '{process_unit.name}' in process pipeline "
                        f"'{pipeline_name}' references unknown shaft '{process_unit.shaft}'. "
                        f"Available shafts in SHAFTS: {available}."
                    )
        return self

    @model_validator(mode="after")
    def validate_shaft_used_by_single_pipeline(self):
        pipelines_by_shaft: dict[ShaftReference, set[str]] = defaultdict(set)
        for pipeline_name, pipeline in self.process_pipelines.items():
            for process_unit in pipeline.process_units:
                if isinstance(process_unit, YamlCompressorProcessUnitInstance):
                    pipelines_by_shaft[process_unit.shaft].add(pipeline_name)

        for shaft_name, pipeline_names in pipelines_by_shaft.items():
            if len(pipeline_names) > 1:
                raise ValueError(
                    f"Shaft '{shaft_name}' is referenced by multiple process pipelines: "
                    f"{', '.join(sorted(pipeline_names))}. A shaft can only be used in one process pipeline."
                )
        return self

    @model_validator(mode="after")
    def validate_drive_train_shaft_references(self):
        if self.energy_network is None:
            return self

        available_shaft_names = {shaft.name for shaft in self.shafts}
        for unit in self.energy_network.units:
            if isinstance(unit, YamlDriveTrain):
                if unit.shaft not in available_shaft_names:
                    available = ", ".join(sorted(available_shaft_names)) or "none"
                    raise ValueError(
                        f"Drive train '{unit.name}' references unknown shaft '{unit.shaft}'. "
                        f"Available shafts in SHAFTS: {available}."
                    )
        return self

    @model_validator(mode="after")
    def validate_shaft_used_by_single_drive_train(self):
        if self.energy_network is None:
            return self

        drive_trains_by_shaft: dict[ShaftReference, set[str]] = defaultdict(set)
        for unit in self.energy_network.units:
            if isinstance(unit, YamlDriveTrain):
                drive_trains_by_shaft[unit.shaft].add(unit.name)

        for shaft_name, drive_train_names in drive_trains_by_shaft.items():
            if len(drive_train_names) > 1:
                raise ValueError(
                    f"Shaft '{shaft_name}' is referenced by multiple drive trains: "
                    f"{', '.join(sorted(drive_train_names))}. A shaft can only be used in one drive train."
                )
        return self
