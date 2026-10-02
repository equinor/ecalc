from collections import defaultdict

from pydantic import ConfigDict, Field, field_validator, model_validator
from pydantic_core.core_schema import ValidationInfo

from libecalc.common.string.string_utils import get_duplicates
from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.components.yaml_installation import YamlInstallation
from libecalc.presentation.yaml.yaml_types.energy.yaml_energy_network import (
    YamlEnergyNetwork,
    YamlMechanicalConsumer,
)
from libecalc.presentation.yaml.yaml_types.facility_model.yaml_facility_model import YamlFacilityModel
from libecalc.presentation.yaml.yaml_types.fuel_type.yaml_fuel_type import YamlFuelType
from libecalc.presentation.yaml.yaml_types.models import YamlConsumerModel, YamlFluidModel
from libecalc.presentation.yaml.yaml_types.process.yaml_fluid_definitions import YamlFluidDefinition
from libecalc.presentation.yaml.yaml_types.process.yaml_process_pipeline import (
    YamlProcessPipeline,
    YamlShaftDrivenProcessUnitInstance,
    describe_process_unit,
)
from libecalc.presentation.yaml.yaml_types.process.yaml_process_references import DefinitionReference
from libecalc.presentation.yaml.yaml_types.process.yaml_process_simulation import (
    YamlEcalcEvent,
    YamlProcessEvent,
    YamlProcessSimulation,
    YamlPumpProcessSimulation,
)
from libecalc.presentation.yaml.yaml_types.process.yaml_process_units import (
    YamlCompressorDefinition,
    YamlProcessUnitDefinition,
)
from libecalc.presentation.yaml.yaml_types.streams.yaml_inlet_stream import YamlInletStream
from libecalc.presentation.yaml.yaml_types.time_series.yaml_time_series import YamlTimeSeriesCollection
from libecalc.presentation.yaml.yaml_types.yaml_default_datetime import YamlDefaultDatetime
from libecalc.presentation.yaml.yaml_types.yaml_shaft import ShaftReference, YamlShaft
from libecalc.presentation.yaml.yaml_types.yaml_variable import YamlVariables
from libecalc.presentation.yaml.yaml_validation_context import YamlModelValidationContextNames


class YamlDefinitions(YamlBase):
    """Definitions section of an eCalc™ yaml file, containing reusable definitions."""

    model_config = ConfigDict(
        title="Definitions",
    )

    process_units: dict[str, YamlProcessUnitDefinition] = Field(
        default_factory=dict,
        title="PROCESS_UNITS",
        description="Defines process units used in PROCESS_PIPELINES.",
    )

    fluids: dict[str, YamlFluidDefinition] = Field(
        default_factory=dict,
        title="FLUIDS",
        description="Defines fluids that can be referenced in inlet streams.",
    )


class YamlAsset(YamlBase):
    """An eCalc™ yaml file"""

    model_config = ConfigDict(
        title="Asset",
    )

    definitions: YamlDefinitions = Field(
        default_factory=YamlDefinitions,
        title="DEFINITIONS",
        description="Contains reusable definitions such as process units and fluids.",
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
    inlet_streams: dict[str, YamlInletStream] = Field(
        default_factory=dict,
        title="INLET_STREAMS",
        description="Defines inlet streams that can be referenced by process system and stream distribution.",
    )
    models: list[YamlConsumerModel] = Field(
        default_factory=list,
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
        default_factory=dict,
        title="VARIABLES",
        description="Defines variables used in an energy usage model by means of expressions or constants."
        "\n\n$ECALC_DOCS_KEYWORDS_URL/VARIABLES",
    )
    shafts: list[YamlShaft] = Field(
        default_factory=list,
        title="SHAFTS",
        description="Defines named shafts representing mechanical connections between drivers and driven equipment.",
    )
    process_pipelines: dict[str, YamlProcessPipeline] = Field(
        default_factory=dict,
        title="PROCESS_PIPELINES",
        description="Defines process pipelines to use in process simulations.",
    )
    process_simulations: list[YamlProcessSimulation] = Field(
        default_factory=list,
        title="PROCESS_SIMULATIONS",
        description="Defines one or more process simulations to be run.",
    )
    ecalc_events: list[YamlEcalcEvent] = Field(
        default_factory=list,
        title="ECALC_EVENTS",
        description="Defines eCalc events associated with temporal model changes",
    )
    energy_network: YamlEnergyNetwork | None = Field(
        None,
        title="ENERGY_NETWORK",
        description="Defines the energy network configuration.",
    )
    process_events: list[YamlProcessEvent] = Field(
        default_factory=list,
        title="PROCESS_EVENTS",
        description="Defines process-specific events that reference global eCalc events.",
    )
    pump_process_simulations: list[YamlPumpProcessSimulation] = Field(
        default_factory=list,
        title="PUMP_PROCESS_SIMULATIONS",
        description="Defines one or more liquid pump process simulations to be run.",
    )
    installations: list[YamlInstallation] = Field(
        ...,
        title="INSTALLATIONS",
        description="Description of the system of energy consumers.\n\n$ECALC_DOCS_KEYWORDS_URL/INSTALLATIONS",
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
    def validate_shaft_references(self):
        available_shaft_names = {shaft.name for shaft in self.shafts}

        for pipeline_name, pipeline in self.process_pipelines.items():
            for position, process_unit in enumerate(pipeline.process_units, start=1):
                if not isinstance(process_unit, YamlShaftDrivenProcessUnitInstance):
                    continue
                if process_unit.shaft not in available_shaft_names:
                    available = ", ".join(sorted(available_shaft_names)) or "none"
                    raise ValueError(
                        f"Process unit {describe_process_unit(process_unit, position)} in process pipeline "
                        f"'{pipeline_name}' references unknown shaft '{process_unit.shaft}'. "
                        f"Available shafts in SHAFTS: {available}."
                    )
        return self

    @model_validator(mode="after")
    def validate_shaft_used_by_single_pipeline(self):
        pipelines_by_shaft: dict[ShaftReference, set[str]] = defaultdict(set)
        for pipeline_name, pipeline in self.process_pipelines.items():
            for process_unit in pipeline.process_units:
                if isinstance(process_unit, YamlShaftDrivenProcessUnitInstance):
                    pipelines_by_shaft[process_unit.shaft].add(pipeline_name)

        for shaft_name, pipeline_names in pipelines_by_shaft.items():
            if len(pipeline_names) > 1:
                raise ValueError(
                    f"Shaft '{shaft_name}' is referenced by multiple process pipelines: "
                    f"{', '.join(sorted(pipeline_names))}. A shaft can only be used in one process pipeline."
                )
        return self

    @model_validator(mode="after")
    def validate_all_compressors_shaft_driven(self):
        for pipeline_name, pipeline in self.process_pipelines.items():
            if not any(isinstance(unit, YamlShaftDrivenProcessUnitInstance) for unit in pipeline.process_units):
                continue

            compressors_without_shaft = [
                describe_process_unit(process_unit, position)
                for position, process_unit in enumerate(pipeline.process_units, start=1)
                if not isinstance(process_unit, YamlShaftDrivenProcessUnitInstance)
                and self._is_compressor(process_unit.target)
            ]
            if compressors_without_shaft:
                raise ValueError(
                    f"Process pipeline '{pipeline_name}' uses SHAFT, but these compressors are missing SHAFT: "
                    f"{', '.join(compressors_without_shaft)}. All compressors in a process pipeline must reference a shaft."
                )
        return self

    def _is_compressor(self, target: YamlProcessUnitDefinition | DefinitionReference) -> bool:
        resolved_target = self.definitions.process_units.get(target) if isinstance(target, str) else target
        return isinstance(resolved_target, YamlCompressorDefinition)

    @model_validator(mode="after")
    def validate_mechanical_consumer_shaft_references(self):
        if self.energy_network is None:
            return self

        available_shaft_names = {shaft.name for shaft in self.shafts}
        for unit in self.energy_network.units:
            if not isinstance(unit, YamlMechanicalConsumer) or unit.shaft is None:
                continue
            if unit.shaft not in available_shaft_names:
                available = ", ".join(sorted(available_shaft_names)) or "none"
                raise ValueError(
                    f"Mechanical consumer '{unit.name}' references unknown shaft '{unit.shaft}'. "
                    f"Available shafts in SHAFTS: {available}."
                )
        return self
