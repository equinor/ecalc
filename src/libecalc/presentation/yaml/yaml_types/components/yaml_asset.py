from pydantic import ConfigDict, Field, field_validator, model_validator
from pydantic_core.core_schema import ValidationInfo

from libecalc.common.string.string_utils import get_duplicates
from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.components.yaml_installation import YamlInstallation
from libecalc.presentation.yaml.yaml_types.components.yaml_process_system import (
    YamlInterstageMixer,
    YamlInterstageSplitter,
    YamlProcessSimulation,
    YamlProcessSystem,
    YamlProcessUnit,
    YamlSerialProcessSystem,
)
from libecalc.presentation.yaml.yaml_types.facility_model.yaml_facility_model import YamlFacilityModel
from libecalc.presentation.yaml.yaml_types.fuel_type.yaml_fuel_type import YamlFuelType
from libecalc.presentation.yaml.yaml_types.models import YamlConsumerModel, YamlFluidModel
from libecalc.presentation.yaml.yaml_types.models.yaml_enums import YamlPressureControl
from libecalc.presentation.yaml.yaml_types.streams.yaml_inlet_stream import YamlInletStream
from libecalc.presentation.yaml.yaml_types.time_series.yaml_time_series import YamlTimeSeriesCollection
from libecalc.presentation.yaml.yaml_types.yaml_default_datetime import YamlDefaultDatetime
from libecalc.presentation.yaml.yaml_types.yaml_variable import YamlVariables
from libecalc.presentation.yaml.yaml_validation_context import YamlModelValidationContextNames


class YamlAsset(YamlBase):
    """An eCalc™ yaml file"""

    model_config = ConfigDict(
        title="Asset",
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
    process_units: dict[str, YamlProcessUnit] = Field(
        default_factory=dict,
        title="PROCESS_UNITS",
        description="Defines process units used in PROCESS_SYSTEMS.",
    )
    process_systems: dict[str, YamlProcessSystem] = Field(
        default_factory=dict,
        title="PROCESS_SYSTEMS",
        description="Defines process systems to use in process simulations.",
    )
    process_simulations: list[YamlProcessSimulation] = Field(
        default_factory=list,
        title="PROCESS_SIMULATIONS",
        description="Defines one or more process simulations to be run.",
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
        ...,
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

    @model_validator(mode="after")
    def validate_unique_references(self):
        references = []

        if self.facility_inputs is not None:
            for facility_input in self.facility_inputs:
                references.append(facility_input.name)

        if self.models is not None:
            for model in self.models:
                references.append(model.name)

        if self.fuel_types is not None:
            for fuel_type in self.fuel_types:
                references.append(fuel_type.name)

        if self.process_systems is not None:
            references.extend(self.process_systems.keys())

        if self.process_units is not None:
            references.extend(self.process_units.keys())

        if self.process_simulations is not None:
            for process_simulation in self.process_simulations:
                references.append(process_simulation.name)

        if self.fluid_models is not None:
            references.extend(self.fluid_models.keys())

        if self.inlet_streams is not None:
            references.extend(self.inlet_streams.keys())

        duplicated_references = get_duplicates(references)

        if len(duplicated_references) > 0:
            raise ValueError(
                f"References/names must be unique across {YamlAsset.model_fields['facility_inputs'].alias}, {YamlAsset.model_fields['models'].alias} and {YamlAsset.model_fields['fuel_types'].alias}."
                f" Duplicated references are: {', '.join(duplicated_references)}"
            )
        return self

    @model_validator(mode="after")
    def validate_simulation_targets_exist(self):
        for sim in self.process_simulations:
            for sim_item in sim.targets:
                train = self.process_systems.get(sim_item.target)
                if not isinstance(train, YamlSerialProcessSystem):
                    valid = [k for k, v in self.process_systems.items() if isinstance(v, YamlSerialProcessSystem)]
                    raise ValueError(
                        f"Target '{sim_item.target}' in simulation '{sim.name}' does not reference a known "
                        f"SERIAL process system. Valid targets are: {', '.join(sorted(valid))}."
                    )
        return self

    @model_validator(mode="after")
    def validate_outlet_constraint_present(self):
        for sim in self.process_simulations:
            for sim_item in sim.targets:
                train = self.process_systems.get(sim_item.target)
                if not isinstance(train, YamlSerialProcessSystem):
                    continue
                if train.name not in sim_item.constraints:
                    raise ValueError(
                        f"Target '{sim_item.target}' in simulation '{sim.name}' has no outlet constraint. "
                        f"Add a constraint keyed by the train name '{train.name}' to define the outlet pressure "
                        f"and pressure control strategy."
                    )
        return self

    @model_validator(mode="after")
    def validate_simulation_streams(self):
        for sim in self.process_simulations:
            for sim_item in sim.targets:
                train = self.process_systems.get(sim_item.target)
                if not isinstance(train, YamlSerialProcessSystem):
                    continue
                for item_ref in train.items:
                    item = self.process_systems.get(item_ref)
                    if isinstance(item, YamlInterstageMixer) and item_ref not in sim_item.mixer_streams:
                        raise ValueError(
                            f"Mixer '{item_ref}' in train '{train.name}' has no stream defined "
                            f"in MIXER_STREAMS of target '{sim_item.target}' in simulation '{sim.name}'."
                        )
                    if isinstance(item, YamlInterstageSplitter) and item_ref not in sim_item.splitter_rates:
                        raise ValueError(
                            f"Splitter '{item_ref}' in train '{train.name}' has no rate defined "
                            f"in SPLITTER_RATES of target '{sim_item.target}' in simulation '{sim.name}'."
                        )
        return self

    @model_validator(mode="after")
    def validate_constraint_order_and_choke_position(self):
        for sim in self.process_simulations:
            for sim_item in sim.targets:
                train = self.process_systems.get(sim_item.target)
                if not isinstance(train, YamlSerialProcessSystem):
                    continue
                topo_order = train.items + [train.name]
                valid_keys = set(topo_order)

                for key in sim_item.constraints:
                    if key not in valid_keys:
                        raise ValueError(
                            f"Constraint key '{key}' in simulation '{sim.name}' is not a valid item name "
                            f"in train '{train.name}' or the train name itself. "
                            f"Valid keys are: {', '.join(topo_order)}."
                        )

                constraint_keys = list(sim_item.constraints.keys())
                positions = [topo_order.index(k) for k in constraint_keys]
                if positions != sorted(positions):
                    raise ValueError(
                        f"Constraints in target '{sim_item.target}' of simulation '{sim.name}' are not in "
                        f"topological order. Expected order: {', '.join(topo_order)}."
                    )

                ordered_keys = [k for k in topo_order if k in sim_item.constraints]
                first_key = ordered_keys[0] if ordered_keys else None
                last_key = ordered_keys[-1] if ordered_keys else None
                for key, constraint in sim_item.constraints.items():
                    if constraint.pressure_control == YamlPressureControl.UPSTREAM_CHOKE and key != first_key:
                        raise ValueError(
                            f"Constraint '{key}' in simulation '{sim.name}' uses UPSTREAM_CHOKE, "
                            f"but UPSTREAM_CHOKE is only valid on the first constraint "
                            f"(keyed by '{first_key}')."
                        )
                    if constraint.pressure_control == YamlPressureControl.DOWNSTREAM_CHOKE and key != last_key:
                        raise ValueError(
                            f"Constraint '{key}' in simulation '{sim.name}' uses DOWNSTREAM_CHOKE, "
                            f"but DOWNSTREAM_CHOKE is only valid on the last constraint "
                            f"(keyed by '{last_key}')."
                        )
        return self

    @model_validator(mode="after")
    def validate_stream_distribution_count(self):
        for sim in self.process_simulations:
            dist = sim.stream_distribution
            n_targets = len(sim.targets)
            if dist.method == "COMMON_STREAM":
                for i, setting in enumerate(dist.settings):
                    if len(setting.rate_fractions) != n_targets:
                        raise ValueError(
                            f"RATE_FRACTIONS entry {i} in simulation '{sim.name}' has "
                            f"{len(setting.rate_fractions)} value(s) but there are {n_targets} target(s). "
                            f"Each RATE_FRACTIONS list must have exactly one fraction per target."
                        )
            elif dist.method == "INDIVIDUAL_STREAMS":
                if len(dist.inlet_streams) != n_targets:
                    raise ValueError(
                        f"INLET_STREAMS in simulation '{sim.name}' has {len(dist.inlet_streams)} stream(s) "
                        f"but there are {n_targets} target(s). "
                        f"Each target must have exactly one inlet stream."
                    )
        return self

    @model_validator(mode="after")
    def validate_no_nested_serial_trains(self):
        for name, system in self.process_systems.items():
            if not isinstance(system, YamlSerialProcessSystem):
                continue
            for item_ref in system.items:
                item = self.process_systems.get(item_ref)
                if isinstance(item, YamlSerialProcessSystem):
                    raise ValueError(
                        f"SERIAL train '{name}' contains item '{item_ref}' which is itself a SERIAL train. "
                        f"SERIAL.items must only reference leaf types: "
                        f"COMPRESSOR_STAGE, PRESSURE_DROP, MIXER, or SPLITTER."
                    )
        return self

    @model_validator(mode="after")
    def validate_mixer_splitter_stream_keys(self):
        for sim in self.process_simulations:
            for sim_item in sim.targets:
                train = self.process_systems.get(sim_item.target)
                if not isinstance(train, YamlSerialProcessSystem):
                    continue
                mixer_refs = {
                    ref for ref in train.items if isinstance(self.process_systems.get(ref), YamlInterstageMixer)
                }
                splitter_refs = {
                    ref for ref in train.items if isinstance(self.process_systems.get(ref), YamlInterstageSplitter)
                }
                for key in sim_item.mixer_streams:
                    if key not in mixer_refs:
                        raise ValueError(
                            f"MIXER_STREAMS key '{key}' in target '{sim_item.target}' of simulation '{sim.name}' "
                            f"does not reference a MIXER item in train '{train.name}'."
                        )
                for key in sim_item.splitter_rates:
                    if key not in splitter_refs:
                        raise ValueError(
                            f"SPLITTER_RATES key '{key}' in target '{sim_item.target}' of simulation '{sim.name}' "
                            f"does not reference a SPLITTER item in train '{train.name}'."
                        )
        return self

    @model_validator(mode="after")
    def validate_overflow_references(self):
        for sim in self.process_simulations:
            dist = sim.stream_distribution
            if dist.method != "COMMON_STREAM":
                continue
            target_names = {sim_item.target for sim_item in sim.targets}
            for i, setting in enumerate(dist.settings):
                for overflow in setting.overflow or []:
                    if overflow.from_reference not in target_names:
                        raise ValueError(
                            f"OVERFLOW FROM_REFERENCE '{overflow.from_reference}' in SETTINGS entry {i} "
                            f"of simulation '{sim.name}' is not a known target. "
                            f"Valid targets: {', '.join(sorted(target_names))}."
                        )
                    if overflow.to_reference not in target_names:
                        raise ValueError(
                            f"OVERFLOW TO_REFERENCE '{overflow.to_reference}' in SETTINGS entry {i} "
                            f"of simulation '{sim.name}' is not a known target. "
                            f"Valid targets: {', '.join(sorted(target_names))}."
                        )
        return self
