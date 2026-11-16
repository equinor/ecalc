from collections import defaultdict
from collections.abc import Iterable
from typing import Annotated, Any, Self

from pydantic import (
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)
from pydantic_core import InitErrorDetails, PydanticCustomError
from pydantic_core.core_schema import ValidationInfo

from libecalc.common.string.string_utils import get_duplicates
from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.components.yaml_installation import YamlInstallation
from libecalc.presentation.yaml.yaml_types.energy.yaml_energy_network import (
    YamlCompressorSampled,
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
    YamlProcessPipeline,
)
from libecalc.presentation.yaml.yaml_types.process.yaml_process_simulation import (
    YamlProcessSimulation,
    YamlPumpProcessSimulation,
)
from libecalc.presentation.yaml.yaml_types.process.yaml_process_units import YamlCompressorModelChart
from libecalc.presentation.yaml.yaml_types.streams.yaml_inlet_stream import YamlInletStream
from libecalc.presentation.yaml.yaml_types.time_series.yaml_time_series import YamlTimeSeriesCollection
from libecalc.presentation.yaml.yaml_types.yaml_compressor import CompressorReference, YamlCompressor
from libecalc.presentation.yaml.yaml_types.yaml_default_datetime import YamlDefaultDatetime
from libecalc.presentation.yaml.yaml_types.yaml_shaft import ShaftReference, YamlShaft
from libecalc.presentation.yaml.yaml_types.yaml_timeline import YamlTimeline
from libecalc.presentation.yaml.yaml_types.yaml_variable import YamlVariables
from libecalc.presentation.yaml.yaml_validation_context import YamlModelValidationContextNames

YamlPerformanceCurveDefinition = Annotated[
    YamlTurbineDefinition | YamlGeneratorDefinition,
    Field(discriminator="type"),
]


class YamlDefinitions(YamlBase):
    """Definitions section of an eCalc™ yaml file, containing reusable definitions."""

    model_config = ConfigDict(
        title="Definitions",
    )

    compressor_models: dict[str, YamlCompressorModelChart] = Field(
        default_factory=dict,
        title="COMPRESSOR_MODELS",
        description="Defines compressor models that can be referenced by name from MODEL of a compressor process unit "
        "in PROCESS_PIPELINES, and from CHANGE_TO of a REBUNDLE change.",
    )

    fluids: dict[str, YamlFluidDefinition] = Field(
        default_factory=dict,
        title="FLUIDS",
        description="Defines fluids that can be referenced in inlet streams.",
    )

    performance_curves: dict[str, YamlPerformanceCurveDefinition] = Field(
        default_factory=dict,
        title="PERFORMANCE_CURVES",
        description="Defines performance curves that can be referenced from GAS_TURBINE, DIESEL_ENGINE, and "
        "GENERATOR_SET units in the ENERGY_NETWORK. TYPE: LOAD_TO_EFFICIENCY (referenced by GAS_TURBINE and "
        "DIESEL_ENGINE) interpolates fuel from a load/efficiency curve: demand below the first LOAD burns the fuel "
        "of the first LOAD, and the last efficiency is used above the last LOAD. TYPE: POWER_TO_FUEL (referenced "
        "by GENERATOR_SET) interpolates fuel directly from a power/fuel curve: below the first POWER the lowest "
        "FUEL is used, and above the last POWER the highest FUEL is used. In both cases the last point is the "
        "maximum power, which is the unit's capacity.",
    )


def _describe_duplicate(name: str, sections: list[str]) -> str:
    unique_sections = sorted(set(sections))
    if len(unique_sections) == 1:
        return f"'{name}' is defined {len(sections)} times in {unique_sections[0]}."
    return f"'{name}' is used in more than one place: {', '.join(unique_sections)}."


class YamlAsset(YamlBase):
    """An eCalc™ yaml file"""

    model_config = ConfigDict(
        title="Asset",
    )

    definitions: YamlDefinitions = Field(
        default_factory=YamlDefinitions,
        title="DEFINITIONS",
        description="Contains reusable definitions.",
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
    inlet_streams: list[YamlInletStream] = Field(
        default_factory=list,
        title="INLET_STREAMS",
        description="Defines inlet streams, each identified by NAME, that a STREAM_DISTRIBUTION can refer to by name.",
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
    shafts: list[YamlShaft] = Field(
        default_factory=list,
        title="SHAFTS",
        description="Defines named shafts representing mechanical connections between drivers and driven equipment.",
    )
    compressors: list[YamlCompressor] = Field(
        default_factory=list,
        title="COMPRESSORS",
        description="Defines the physical compressors in the model. Compressor process units in PROCESS_PIPELINES and "
        "COMPRESSOR_SAMPLED units in ENERGY_NETWORK refer to a compressor by name with COMPRESSOR.",
    )
    process_pipelines: list[YamlProcessPipeline] = Field(
        default_factory=list,
        title="PROCESS_PIPELINES",
        description="Defines process pipelines, each identified by NAME, to use in process simulations.",
    )
    process_simulations: list[YamlProcessSimulation] = Field(
        default_factory=list,
        title="PROCESS_SIMULATIONS",
        description="Defines one or more process simulations to be run.",
    )

    energy_network: YamlEnergyNetwork | None = Field(
        None,
        title="ENERGY_NETWORK",
        description="Defines the energy network configuration.",
    )

    timeline: YamlTimeline | None = Field(
        None,
        title="TIMELINE",
        description="Defines dated events in the model. Event dates are added to the time steps of process "
        "simulations and the energy network. Replaces ECALC_EVENTS and PROCESS_EVENTS",
    )
    pump_process_simulations: list[YamlPumpProcessSimulation] = Field(
        default_factory=list,
        title="PUMP_PROCESS_SIMULATIONS",
        description="Defines one or more liquid pump process simulations to be run.",
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
    def validate_legacy_or_nextgen(self, info: ValidationInfo):
        nextgen = (info.context or {}).get(YamlModelValidationContextNames.nextgen)
        if nextgen is None:
            return self

        unavailable = _aliases((LEGACY_ROOT_FIELDS if nextgen else NEXTGEN_ROOT_FIELDS) & self.model_fields_set)
        if unavailable:
            raise ValueError(
                f"The following elements are not available in a {'NextGen' if nextgen else 'legacy'} model: "
                f"{', '.join(unavailable)}."
            )

        missing = _aliases(get_required_root_field_names(nextgen) - self.model_fields_set)
        if missing:
            raise ValueError(
                f"The following elements are required in a {'NextGen' if nextgen else 'legacy'} model: "
                f"{', '.join(missing)}."
            )
        return self

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

    @field_validator("compressors", mode="after")
    @classmethod
    def validate_unique_compressor_names(
        cls, compressors: list[YamlCompressor], info: ValidationInfo
    ) -> list[YamlCompressor]:
        duplicated_names = get_duplicates(compressor.name for compressor in compressors)
        if duplicated_names:
            field_name = info.field_name
            alias = cls.model_fields[field_name].alias if field_name is not None else "COMPRESSORS"
            raise ValueError(
                f"{alias} names must be unique. Duplicated names are: {', '.join(sorted(duplicated_names))}"
            )
        return compressors

    @field_validator("inlet_streams", "process_pipelines", mode="before")
    @classmethod
    def validate_named_list_is_not_mapping(cls, value: Any, info: ValidationInfo) -> Any:
        if isinstance(value, dict):
            field_name = info.field_name
            alias = cls.model_fields[field_name].alias if field_name is not None else "This section"
            raise ValueError(
                f"{alias} is a list of items identified by NAME. "
                "Give each item as a list item with NAME, not as a key in a mapping."
            )
        return value

    def _process_compressor_models(self) -> list[tuple[CompressorReference, str]]:
        """Every model of a compressor in the process domain, as (compressor, human-readable location)."""
        return [
            (compressor, f"process pipeline '{pipeline.name}'")
            for pipeline in self.process_pipelines
            for compressor in pipeline.compressors
        ]

    def _sampled_compressor_models(self) -> list[tuple[CompressorReference, str]]:
        """Every COMPRESSOR_SAMPLED unit, as (compressor, human-readable location)."""
        if self.energy_network is None:
            return []
        return [
            (unit.compressor, "a COMPRESSOR_SAMPLED unit")
            for unit in self.energy_network.units
            if isinstance(unit, YamlCompressorSampled)
        ]

    def _energy_compressor_models(self) -> list[tuple[CompressorReference, str]]:
        """
        Every model of a compressor in the energy domain, as (compressor, human-readable location).

        A DRIVE_TRAIN models each compressor on its shaft; a COMPRESSOR_SAMPLED unit models its compressor.
        """
        if self.energy_network is None:
            return []
        compressors_by_shaft = {shaft.name: shaft.compressors for shaft in self.shafts}
        drive_train_models = [
            (compressor, f"the DRIVE_TRAIN for shaft '{unit.shaft}'")
            for unit in self.energy_network.units
            if isinstance(unit, YamlDriveTrain)
            for compressor in compressors_by_shaft.get(unit.shaft, [])
        ]
        return drive_train_models + self._sampled_compressor_models()

    def _shaft_compressor_references(self) -> list[tuple[CompressorReference, str]]:
        """Every compressor listed in SHAFTS, as (compressor, human-readable location)."""
        return [(compressor, f"shaft '{shaft.name}'") for shaft in self.shafts for compressor in shaft.compressors]

    def _shaft_by_compressor(self) -> dict[CompressorReference, ShaftReference]:
        return {compressor: shaft.name for shaft in self.shafts for compressor in shaft.compressors}

    def _shafts_by_pipeline(self) -> dict[str, set[ShaftReference]]:
        """The shafts of the compressors in each process pipeline. A compressor on no shaft is reported elsewhere."""
        shaft_by_compressor = self._shaft_by_compressor()
        return {
            pipeline.name: {
                shaft_by_compressor[compressor]
                for compressor in pipeline.compressors
                if compressor in shaft_by_compressor
            }
            for pipeline in self.process_pipelines
        }

    @model_validator(mode="after")
    def validate_compressor_references(self):
        available_compressor_names = {compressor.name for compressor in self.compressors}
        locations_by_unknown_compressor: dict[CompressorReference, list[str]] = defaultdict(list)
        for compressor_reference, location in (
            self._process_compressor_models() + self._sampled_compressor_models() + self._shaft_compressor_references()
        ):
            if compressor_reference not in available_compressor_names:
                locations_by_unknown_compressor[compressor_reference].append(location)

        if locations_by_unknown_compressor:
            available = ", ".join(sorted(available_compressor_names)) or "none"
            violations = [
                f"Compressor '{compressor_name}' referenced in {', '.join(locations)} is not defined."
                for compressor_name, locations in locations_by_unknown_compressor.items()
            ]
            raise ValueError("\n".join([*violations, f"Available compressors in COMPRESSORS: {available}."]))
        return self

    @model_validator(mode="after")
    def validate_compressor_on_single_shaft(self):
        shafts_by_compressor: dict[CompressorReference, list[ShaftReference]] = defaultdict(list)
        for shaft in self.shafts:
            for compressor in shaft.compressors:
                shafts_by_compressor[compressor].append(shaft.name)

        violations = [
            f"Compressor '{compressor_name}' is listed more than once in SHAFTS, on shafts: {', '.join(shaft_names)}."
            for compressor_name, shaft_names in shafts_by_compressor.items()
            if len(shaft_names) > 1
        ]
        if violations:
            raise ValueError("\n".join([*violations, "A compressor can be listed on one shaft only."]))
        return self

    @model_validator(mode="after")
    def validate_compressor_modelled_once_per_domain(self):
        """The compressor id is used as process unit id and as energy unit id, so each domain can model it once."""
        violations: list[str] = []
        for domain, models in (
            ("process", self._process_compressor_models()),
            ("energy", self._energy_compressor_models()),
        ):
            locations_by_compressor: dict[CompressorReference, list[str]] = defaultdict(list)
            for compressor_reference, location in models:
                locations_by_compressor[compressor_reference].append(location)

            violations.extend(
                f"Compressor '{compressor_name}' is modelled more than once in the {domain} domain: "
                f"{', '.join(locations)}."
                for compressor_name, locations in locations_by_compressor.items()
                if len(locations) > 1
            )

        if violations:
            raise ValueError("\n".join([*violations, "Each domain can model a compressor at most once."]))
        return self

    @model_validator(mode="after")
    def validate_unique_references(self) -> Self:
        # Each entry is (dotted yaml path, names), so a duplicate can be reported with a precise location.
        sections: tuple[tuple[str, Iterable[str]], ...] = (
            ("FACILITY_INPUTS", (facility_input.name for facility_input in self.facility_inputs)),
            ("MODELS", (model.name for model in self.models)),
            ("FUEL_TYPES", (fuel_type.name for fuel_type in self.fuel_types)),
            ("PROCESS_PIPELINES", (pipeline.name for pipeline in self.process_pipelines)),
            ("DEFINITIONS.COMPRESSOR_MODELS", self.definitions.compressor_models.keys()),
            ("DEFINITIONS.FLUIDS", self.definitions.fluids.keys()),
            ("DEFINITIONS.PERFORMANCE_CURVES", self.definitions.performance_curves.keys()),
            ("PROCESS_SIMULATIONS", (process_simulation.name for process_simulation in self.process_simulations)),
            (
                "PUMP_PROCESS_SIMULATIONS",
                (pump_process_simulation.name for pump_process_simulation in self.pump_process_simulations),
            ),
            ("FLUID_MODELS", self.fluid_models.keys()),
            ("INLET_STREAMS", (inlet_stream.name for inlet_stream in self.inlet_streams)),
            ("TIMELINE.EVENTS", self.timeline.events.keys() if self.timeline is not None else ()),
        )

        sections_by_name: dict[str, list[str]] = defaultdict(list)
        for section, names in sections:
            for name in names:
                sections_by_name[name].append(section)

        line_errors = [
            InitErrorDetails(
                type=PydanticCustomError("duplicate_reference", "{message}", {"message": message}),
                loc=(*section.split("."), name),
                input=name,
            )
            for name, found_sections in sections_by_name.items()
            if len(found_sections) > 1
            for message in (_describe_duplicate(name, found_sections),)
            # Same-section repeats share an identical yaml path (the path is the name itself); keep one.
            for section in dict.fromkeys(found_sections)
        ]
        if line_errors:
            raise ValidationError.from_exception_data(self.__class__.__name__, line_errors)
        return self

    @model_validator(mode="after")
    def validate_constraint_process_units(self):
        """A constraint splits its pipeline after a compressor, so PROCESS_UNIT names a compressor in that pipeline."""
        compressors_by_pipeline = {pipeline.name: pipeline.compressors for pipeline in self.process_pipelines}
        violations: list[str] = []
        for simulation in self.process_simulations:
            for pipeline_name, constraints in simulation.constraints.items():
                compressors = compressors_by_pipeline.get(pipeline_name)
                if compressors is None:
                    continue
                violations.extend(
                    f"CONSTRAINTS PROCESS_UNIT '{constraint.process_unit}' of process simulation '{simulation.name}' is "
                    f"not a compressor in process pipeline '{pipeline_name}'. "
                    f"Compressors in this pipeline: {', '.join(compressors) or 'none'}."
                    for constraint in constraints
                    if constraint.process_unit is not None and constraint.process_unit not in compressors
                )
        if violations:
            raise ValueError("\n".join(violations))
        return self

    @model_validator(mode="after")
    def validate_process_compressors_on_shaft(self):
        """The process simulation finds a compressor's speed through its shaft."""
        shaft_by_compressor = self._shaft_by_compressor()
        violations = [
            f"Compressor '{compressor_name}' in {location} is not on a shaft."
            for compressor_name, location in self._process_compressor_models()
            if compressor_name not in shaft_by_compressor
        ]
        if violations:
            raise ValueError(
                "\n".join(
                    [
                        *violations,
                        "Add each compressor placed in a process pipeline to COMPRESSORS of a shaft in SHAFTS.",
                    ]
                )
            )
        return self

    @model_validator(mode="after")
    def validate_pipeline_on_single_shaft(self):
        violations = [
            f"Process pipeline '{pipeline_name}' has compressors on multiple shafts: {', '.join(sorted(shaft_names))}."
            for pipeline_name, shaft_names in self._shafts_by_pipeline().items()
            if len(shaft_names) > 1
        ]
        if violations:
            raise ValueError("\n".join([*violations, "Multiple shafts in one process pipeline are not supported yet."]))
        return self

    @model_validator(mode="after")
    def validate_shaft_used_by_single_pipeline(self):
        pipelines_by_shaft: dict[ShaftReference, set[str]] = defaultdict(set)
        for pipeline_name, shaft_names in self._shafts_by_pipeline().items():
            for shaft_name in shaft_names:
                pipelines_by_shaft[shaft_name].add(pipeline_name)

        violations = [
            f"Shaft '{shaft_name}' has compressors in multiple process pipelines: {', '.join(sorted(pipeline_names))}."
            for shaft_name, pipeline_names in pipelines_by_shaft.items()
            if len(pipeline_names) > 1
        ]
        if violations:
            raise ValueError("\n".join([*violations, "A shaft can only be used in one process pipeline."]))
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
                        f"A drive train references unknown shaft '{unit.shaft}'. "
                        f"Available shafts in SHAFTS: {available}."
                    )
        return self

    @model_validator(mode="after")
    def validate_drive_train_mechanical_efficiency_compressors(self):
        if self.energy_network is None:
            return self

        compressors_by_shaft = {shaft.name: shaft.compressors for shaft in self.shafts}
        violations = [
            f"The drive train for shaft '{unit.shaft}' gives a mechanical efficiency for compressor "
            f"'{entry.compressor}', which is not on that shaft. "
            f"Compressors on this shaft: {', '.join(compressors_by_shaft[unit.shaft]) or 'none'}."
            for unit in self.energy_network.units
            if isinstance(unit, YamlDriveTrain) and unit.shaft in compressors_by_shaft
            for entry in unit.mechanical_efficiencies
            if entry.compressor not in compressors_by_shaft[unit.shaft]
        ]
        if violations:
            raise ValueError(
                "\n".join(
                    [*violations, "MECHANICAL_EFFICIENCIES can only list compressors on the drive train's shaft."]
                )
            )
        return self

    @model_validator(mode="after")
    def validate_shaft_used_by_single_drive_train(self):
        if self.energy_network is None:
            return self

        drive_train_count_by_shaft: dict[ShaftReference, int] = defaultdict(int)
        for unit in self.energy_network.units:
            if isinstance(unit, YamlDriveTrain):
                drive_train_count_by_shaft[unit.shaft] += 1

        for shaft_name, drive_train_count in drive_train_count_by_shaft.items():
            if drive_train_count > 1:
                raise ValueError(
                    f"Shaft '{shaft_name}' is referenced by {drive_train_count} drive trains. "
                    f"A shaft can only be used in one drive train."
                )
        return self

    @model_validator(mode="after")
    def validate_driven_shafts(self):
        """
        A DRIVE_TRAIN's demand is the shaft power of the compressors on its shaft, taken from their process
        simulation. A driven shaft with no compressors, or with a compressor no simulation solves, would silently lose
        demand.
        """
        if self.energy_network is None:
            return self

        compressors_by_shaft = {shaft.name: shaft.compressors for shaft in self.shafts}
        targeted_pipelines = {target for simulation in self.process_simulations for target in simulation.targets}
        pipeline_by_compressor = {
            compressor: pipeline.name for pipeline in self.process_pipelines for compressor in pipeline.compressors
        }

        violations: list[str] = []
        for unit in self.energy_network.units:
            if not isinstance(unit, YamlDriveTrain):
                continue
            compressors = compressors_by_shaft.get(unit.shaft, [])
            if not compressors:
                violations.append(
                    f"A drive train drives shaft '{unit.shaft}', which has no compressors. "
                    f"List the compressors on the shaft in COMPRESSORS of the shaft in SHAFTS."
                )
            for compressor_name in compressors:
                pipeline_name = pipeline_by_compressor.get(compressor_name)
                if pipeline_name in targeted_pipelines:
                    continue
                placement = (
                    "is not placed in any process pipeline"
                    if pipeline_name is None
                    else f"is placed in process pipeline '{pipeline_name}', which no process simulation targets"
                )
                violations.append(
                    f"Compressor '{compressor_name}' on shaft '{unit.shaft}', driven by a drive train, {placement}."
                )
        if violations:
            raise ValueError(
                "\n".join(
                    [
                        *violations,
                        "A drive train gets its demand from the process simulation of each compressor on its shaft.",
                    ]
                )
            )
        return self


COMMON_ROOT_FIELDS = frozenset({"time_series", "variables", "facility_inputs", "start", "end"})
LEGACY_ROOT_FIELDS = frozenset({"fluid_models", "models", "fuel_types", "installations"})
NEXTGEN_ROOT_FIELDS = frozenset(
    {
        "definitions",
        "inlet_streams",
        "shafts",
        "compressors",
        "process_pipelines",
        "process_simulations",
        "pump_process_simulations",
        "energy_network",
        "timeline",
    }
)
LEGACY_REQUIRED_ROOT_FIELDS = frozenset({"fuel_types", "installations"})


def _aliases(field_names: Iterable[str]) -> list[str]:
    return sorted(YamlAsset.model_fields[field_name].alias or field_name.upper() for field_name in field_names)


def get_root_field_names(nextgen: bool) -> set[str]:
    return set(COMMON_ROOT_FIELDS | (NEXTGEN_ROOT_FIELDS if nextgen else LEGACY_ROOT_FIELDS))


def get_required_root_field_names(nextgen: bool) -> set[str]:
    return set() if nextgen else set(LEGACY_REQUIRED_ROOT_FIELDS)
