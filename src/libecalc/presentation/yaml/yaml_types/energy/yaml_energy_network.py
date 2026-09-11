from enum import StrEnum
from typing import Annotated, Literal, Union

from pydantic import ConfigDict, Field, field_validator, model_validator

from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.components.yaml_expression_type import YamlExpressionType
from libecalc.presentation.yaml.yaml_validators.file_validators import file_exists_validator


def _check_non_negative(v: YamlExpressionType | None, field_name: str) -> YamlExpressionType | None:
    if isinstance(v, (int, float)) and v < 0:
        raise ValueError(f"{field_name} must be non-negative, got {v}")
    return v


def _check_efficiency(v: YamlExpressionType | None) -> YamlExpressionType | None:
    if isinstance(v, (int, float)) and not (0 < v <= 1):
        raise ValueError(f"EFFICIENCY must be in (0, 1], got {v}")
    return v


def _check_at_least_one_sampled_variable(
    name: str,
    rate: YamlExpressionType | None,
    suction_pressure: YamlExpressionType | None,
    discharge_pressure: YamlExpressionType | None,
) -> None:
    if rate is None and suction_pressure is None and discharge_pressure is None:
        raise ValueError(f"'{name}': at least one of RATE/SUCTION_PRESSURE/DISCHARGE_PRESSURE must be specified.")


class YamlEnergySourceType(StrEnum):
    FUEL_GAS_SOURCE = "FUEL_GAS_SOURCE"
    ELECTRICAL_SOURCE = "ELECTRICAL_SOURCE"
    DIESEL_SOURCE = "DIESEL_SOURCE"


class YamlEnergySource(YamlBase):
    model_config = ConfigDict(title="EnergySource")

    name: Annotated[
        str,
        Field(
            title="NAME",
            description="Unique name for this energy source.",
        ),
    ]
    type: Annotated[
        YamlEnergySourceType,
        Field(
            title="TYPE",
            description="Type of external energy source.",
        ),
    ]
    capacity: Annotated[
        YamlExpressionType | None,
        Field(
            title="CAPACITY",
            description="Maximum output capacity. Omit for unlimited.",
        ),
    ] = None

    @field_validator("capacity", mode="after")
    @classmethod
    def _capacity_non_negative(cls, v: YamlExpressionType | None) -> YamlExpressionType | None:
        return _check_non_negative(v, "CAPACITY")


class YamlConverterBase(YamlBase):
    name: Annotated[
        str,
        Field(
            title="NAME",
            description="Unique name for this component.",
        ),
    ]
    input: Annotated[
        str,
        Field(
            title="INPUT",
            description="Source or component this receives energy from.",
        ),
    ]
    capacity: Annotated[
        YamlExpressionType | None,
        Field(
            title="CAPACITY",
            description="Maximum output capacity. Omit for unlimited.",
        ),
    ] = None

    @field_validator("capacity", mode="after")
    @classmethod
    def _capacity_non_negative(cls, v: YamlExpressionType | None) -> YamlExpressionType | None:
        return _check_non_negative(v, "CAPACITY")


class YamlGeneratorSet(YamlConverterBase):
    model_config = ConfigDict(title="GeneratorSet")

    type: Literal["GENERATOR_SET"]
    model: Annotated[
        str | None,
        Field(
            title="MODEL",
            description="Reference to a facility model defining the power-to-fuel curve.",
        ),
    ] = None


class YamlGasTurbine(YamlConverterBase):
    model_config = ConfigDict(title="GasTurbine")

    type: Literal["GAS_TURBINE"]
    model: Annotated[
        str | None,
        Field(
            title="MODEL",
            description="Reference to a facility model defining the power-to-fuel curve.",
        ),
    ] = None


class YamlElectricalMotor(YamlConverterBase):
    model_config = ConfigDict(title="ElectricalMotor")

    type: Literal["ELECTRICAL_MOTOR"]
    efficiency: Annotated[
        YamlExpressionType | None,
        Field(
            title="EFFICIENCY",
            description="Conversion efficiency (0–1]. Defaults to 0.95 if omitted.",
        ),
    ] = None

    @field_validator("efficiency", mode="after")
    @classmethod
    def _efficiency_in_range(cls, v: YamlExpressionType | None) -> YamlExpressionType | None:
        return _check_efficiency(v)


class YamlElectricalCable(YamlConverterBase):
    model_config = ConfigDict(title="ElectricalCable")

    type: Literal["ELECTRICAL_CABLE"]
    efficiency: Annotated[
        YamlExpressionType | None,
        Field(
            title="EFFICIENCY",
            description="Transmission efficiency (0–1]. 1.0 means no loss. Defaults to 1.0 if omitted.",
        ),
    ] = None

    @field_validator("efficiency", mode="after")
    @classmethod
    def _efficiency_in_range(cls, v: YamlExpressionType | None) -> YamlExpressionType | None:
        return _check_efficiency(v)


class YamlDispatchStrategy(StrEnum):
    PRIORITY = "PRIORITY"
    EQUAL_SPLIT = "EQUAL_SPLIT"


class YamlJunctionBase(YamlBase):
    name: Annotated[
        str,
        Field(
            title="NAME",
            description="Unique name for this component.",
        ),
    ]
    input: Annotated[
        list[str],
        Field(
            title="INPUT",
            description="Sources or units feeding into this junction.",
        ),
    ]
    dispatch_strategy: Annotated[
        YamlDispatchStrategy | None,
        Field(
            title="DISPATCH_STRATEGY",
            description="How to allocate demand across multiple inputs. Required when INPUT has more than one entry.",
        ),
    ] = None

    @model_validator(mode="after")
    def check_dispatch_strategy_required_for_fan_in(self):
        if len(self.input) > 1 and self.dispatch_strategy is None:
            raise ValueError(f"'{self.name}': DISPATCH_STRATEGY is required when INPUT has multiple entries.")
        return self

    @model_validator(mode="after")
    def check_no_duplicate_inputs(self):
        if len(self.input) != len(set(self.input)):
            duplicates = [ref for ref in self.input if self.input.count(ref) > 1]
            raise ValueError(f"'{self.name}': duplicate INPUT references: {set(duplicates)}")
        return self


class YamlElectricalBus(YamlJunctionBase):
    model_config = ConfigDict(title="ElectricalBus")

    type: Literal["ELECTRICAL_BUS"]


class YamlFuelGasManifold(YamlJunctionBase):
    model_config = ConfigDict(title="FuelGasManifold")

    type: Literal["FUEL_GAS_MANIFOLD"]


class YamlConsumerBase(YamlBase):
    name: Annotated[
        str,
        Field(
            title="NAME",
            description="Unique name for this component.",
        ),
    ]
    input: Annotated[
        str,
        Field(
            title="INPUT",
            description="Source or component this receives energy from.",
        ),
    ]


class YamlElectricalConsumer(YamlConsumerBase):
    model_config = ConfigDict(title="ElectricalConsumer")

    type: Literal["ELECTRICAL_CONSUMER"]
    load: Annotated[
        YamlExpressionType,
        Field(
            title="LOAD",
            description="Electrical power demand (MW).",
        ),
    ]

    @field_validator("load", mode="after")
    @classmethod
    def _load_non_negative(cls, v: YamlExpressionType) -> YamlExpressionType:
        return _check_non_negative(v, "LOAD")  # type: ignore[return-value]


class YamlMechanicalConsumer(YamlConsumerBase):
    model_config = ConfigDict(title="MechanicalConsumer")

    type: Literal["MECHANICAL_CONSUMER"]
    load: Annotated[
        YamlExpressionType | None,
        Field(
            title="LOAD",
            description="Shaft power demand (MW). Mutually exclusive with PROCESS_SIMULATION.",
        ),
    ] = None
    process_simulation: Annotated[
        str | None,
        Field(
            title="PROCESS_SIMULATION",
            description="Reference to a process simulation that determines shaft power demand. Mutually exclusive with LOAD.",
        ),
    ] = None

    @field_validator("load", mode="after")
    @classmethod
    def _load_non_negative(cls, v: YamlExpressionType | None) -> YamlExpressionType | None:
        return _check_non_negative(v, "LOAD")

    @model_validator(mode="after")
    def check_exactly_one_demand_source(self):
        if self.load is None and self.process_simulation is None:
            raise ValueError(f"'{self.name}': either LOAD or PROCESS_SIMULATION must be specified.")
        if self.load is not None and self.process_simulation is not None:
            raise ValueError(f"'{self.name}': cannot specify both LOAD and PROCESS_SIMULATION.")
        return self


class YamlFuelGasConsumer(YamlConsumerBase):
    model_config = ConfigDict(title="FuelGasConsumer")

    type: Literal["FUEL_GAS_CONSUMER"]
    rate: Annotated[
        YamlExpressionType,
        Field(
            title="RATE",
            description="Fuel gas consumption rate (Sm³/d).",
        ),
    ]

    @field_validator("rate", mode="after")
    @classmethod
    def _rate_non_negative(cls, v: YamlExpressionType) -> YamlExpressionType:
        return _check_non_negative(v, "RATE")  # type: ignore[return-value]


class YamlSampledCompressor(YamlConsumerBase):
    """A compressor modelled directly from tabulated energy usage data in FILE, with no
    separate MODELS definition or manual turbine/compressor wiring required. The energy
    usage type is not declared here: it is detected from which of the RATE,
    SUCTION_PRESSURE, DISCHARGE_PRESSURE, FUEL, and POWER columns are present as headers in
    FILE, matching the legacy COMPRESSOR_TABULAR facility model.

    Only FUEL present: fuel gas is consumed directly, with no explicit turbine/compressor
    split (INPUT must provide fuel gas, e.g. a source or manifold).
    Only POWER present: POWER is interpreted according to what INPUT provides — electrical
    power, consumed directly with no explicit motor/compressor split, if INPUT provides
    electrical power (e.g. a generator set, bus, or cable); or mechanical power, consumed
    directly with no explicit turbine/compressor split, if INPUT provides mechanical power
    (e.g. an explicitly modelled GAS_TURBINE or ELECTRICAL_MOTOR upstream).
    Both present: a turbine (fuel -> mechanical power, so INPUT must provide fuel gas)
    drives a compressor (FUEL and POWER, resolved together from FILE
    at the same operating point, giving the turbine its already-known fuel for that
    power); both units are built and wired together automatically from this single
    definition.

    At least one of RATE/SUCTION_PRESSURE/DISCHARGE_PRESSURE must be given to query FILE for
    the actual usage/prediction values.
    """

    model_config = ConfigDict(title="SampledCompressor")

    type: Literal["SAMPLED_COMPRESSOR"]
    file: Annotated[
        str,
        Field(
            title="FILE",
            description="Reference to a file tabulating energy usage against RATE, SUCTION_PRESSURE, "
            "and/or DISCHARGE_PRESSURE.",
        ),
    ]
    rate: Annotated[
        YamlExpressionType | None,
        Field(
            title="RATE",
            description="Fluid rate through the compressor (Sm³/d), queried against FILE.",
        ),
    ] = None
    suction_pressure: Annotated[
        YamlExpressionType | None,
        Field(
            title="SUCTION_PRESSURE",
            description="Compressor inlet pressure (bara), queried against FILE.",
        ),
    ] = None
    discharge_pressure: Annotated[
        YamlExpressionType | None,
        Field(
            title="DISCHARGE_PRESSURE",
            description="Compressor outlet pressure (bara), queried against FILE.",
        ),
    ] = None

    validate_file_exists = field_validator("file", mode="after")(file_exists_validator)

    @field_validator("rate", mode="after")
    @classmethod
    def _rate_non_negative(cls, v: YamlExpressionType | None) -> YamlExpressionType | None:
        return _check_non_negative(v, "RATE")

    @field_validator("suction_pressure", mode="after")
    @classmethod
    def _suction_pressure_non_negative(cls, v: YamlExpressionType | None) -> YamlExpressionType | None:
        return _check_non_negative(v, "SUCTION_PRESSURE")

    @field_validator("discharge_pressure", mode="after")
    @classmethod
    def _discharge_pressure_non_negative(cls, v: YamlExpressionType | None) -> YamlExpressionType | None:
        return _check_non_negative(v, "DISCHARGE_PRESSURE")

    @model_validator(mode="after")
    def check_at_least_one_variable(self):
        _check_at_least_one_sampled_variable(
            self.name,
            rate=self.rate,
            suction_pressure=self.suction_pressure,
            discharge_pressure=self.discharge_pressure,
        )
        return self


class _SampledFuelGasConsumer(YamlSampledCompressor):
    """Produced by expand_sampled_compressors when FILE has only a FUEL column: FILE's
    energy usage is consumed directly as fuel gas, with no separate turbine/compressor
    split. Not a member of YamlComponent, so it can never be parsed from user YAML."""


class _SampledElectricalConsumer(YamlSampledCompressor):
    """Produced by expand_sampled_compressors when FILE has only a POWER column and
    INPUT provides electrical power: FILE's energy usage is consumed directly as
    electrical power, with no separate motor/compressor split. Not a member of
    YamlComponent, so it can never be parsed from user YAML."""


class _SampledGasTurbine(YamlSampledCompressor):
    """The fuel -> mechanical power half of expand_sampled_compressors's split, produced
    when FILE has both FUEL and POWER columns. Not a member of YamlComponent, so it can
    never be parsed from user YAML."""


class _SampledMechanicalConsumer(YamlSampledCompressor):
    """The mechanical power -> none half of expand_sampled_compressors's split, fed by
    the paired _SampledGasTurbine. Also produced directly when FILE has only a POWER
    column and INPUT already provides mechanical power (e.g. an explicitly modelled
    upstream GAS_TURBINE or ELECTRICAL_MOTOR), in which case there is no paired
    _SampledGasTurbine — FILE's energy usage is consumed directly as mechanical power.
    Not a member of YamlComponent, so it can never be parsed from user YAML."""


class YamlDieselConsumer(YamlConsumerBase):
    model_config = ConfigDict(title="DieselConsumer")

    type: Literal["DIESEL_CONSUMER"]
    rate: Annotated[
        YamlExpressionType,
        Field(
            title="RATE",
            description="Diesel consumption rate (l/d).",
        ),
    ]

    @field_validator("rate", mode="after")
    @classmethod
    def _rate_non_negative(cls, v: YamlExpressionType) -> YamlExpressionType:
        return _check_non_negative(v, "RATE")  # type: ignore[return-value]


YamlComponent = Annotated[
    Union[
        YamlGeneratorSet,
        YamlGasTurbine,
        YamlElectricalMotor,
        YamlElectricalCable,
        YamlElectricalBus,
        YamlFuelGasManifold,
        YamlElectricalConsumer,
        YamlMechanicalConsumer,
        YamlFuelGasConsumer,
        YamlDieselConsumer,
        YamlSampledCompressor,
    ],
    Field(discriminator="type"),
]


class EnergyType(StrEnum):
    FUEL_GAS = "FUEL_GAS"
    ELECTRICAL = "ELECTRICAL"
    MECHANICAL = "MECHANICAL"
    DIESEL = "DIESEL"


INPUT_ENERGY: dict[str, EnergyType] = {
    "GENERATOR_SET": EnergyType.FUEL_GAS,
    "GAS_TURBINE": EnergyType.FUEL_GAS,
    "ELECTRICAL_MOTOR": EnergyType.ELECTRICAL,
    "ELECTRICAL_CABLE": EnergyType.ELECTRICAL,
    "ELECTRICAL_BUS": EnergyType.ELECTRICAL,
    "FUEL_GAS_MANIFOLD": EnergyType.FUEL_GAS,
    "ELECTRICAL_CONSUMER": EnergyType.ELECTRICAL,
    "MECHANICAL_CONSUMER": EnergyType.MECHANICAL,
    "FUEL_GAS_CONSUMER": EnergyType.FUEL_GAS,
    "DIESEL_CONSUMER": EnergyType.DIESEL,
}

# SAMPLED_COMPRESSOR has no single fixed entry in INPUT_ENERGY: its real input energy
# type (fuel gas, electrical, or mechanical) is only known once FILE's columns have been
# read, at mapper time. At schema time we only know it must be one of these three; the
# mapper's validate_input_energy_type narrows it to the actual one detected from FILE.
INPUT_ENERGY_ALTERNATIVES: dict[str, set[EnergyType]] = {
    "SAMPLED_COMPRESSOR": {EnergyType.FUEL_GAS, EnergyType.ELECTRICAL, EnergyType.MECHANICAL},
}

OUTPUT_ENERGY: dict[str, EnergyType] = {
    "GENERATOR_SET": EnergyType.ELECTRICAL,
    "GAS_TURBINE": EnergyType.MECHANICAL,
    "ELECTRICAL_MOTOR": EnergyType.MECHANICAL,
    "ELECTRICAL_CABLE": EnergyType.ELECTRICAL,
    "ELECTRICAL_BUS": EnergyType.ELECTRICAL,
    "FUEL_GAS_MANIFOLD": EnergyType.FUEL_GAS,
}

SOURCE_OUTPUT_ENERGY: dict[YamlEnergySourceType, EnergyType] = {
    YamlEnergySourceType.FUEL_GAS_SOURCE: EnergyType.FUEL_GAS,
    YamlEnergySourceType.DIESEL_SOURCE: EnergyType.DIESEL,
    YamlEnergySourceType.ELECTRICAL_SOURCE: EnergyType.ELECTRICAL,
}

CONSUMER_TYPES = (set(INPUT_ENERGY) - set(OUTPUT_ENERGY)) | set(INPUT_ENERGY_ALTERNATIVES)


def _get_input_names(component: YamlComponent) -> list[str]:
    if isinstance(component.input, list):
        return component.input
    return [component.input]


class YamlEnergyNetwork(YamlBase):
    model_config = ConfigDict(title="EnergyNetwork")

    sources: Annotated[
        list[YamlEnergySource],
        Field(
            min_length=1,
            title="SOURCES",
            description="External energy entering the system (fuel gas, electrical, diesel).",
        ),
    ]
    units: Annotated[
        list[YamlComponent],
        Field(
            title="UNITS",
            description="Converters, junctions, and consumers forming the energy network.",
        ),
    ] = []

    def _all_names(self) -> list[str]:
        return [s.name for s in self.sources] + [c.name for c in self.units]

    def _valid_input_names(self) -> set[str]:
        names = {s.name for s in self.sources}
        names.update(c.name for c in self.units if c.type not in CONSUMER_TYPES)
        return names

    @model_validator(mode="after")
    def check_unique_names(self):
        seen: set[str] = set()
        duplicates: set[str] = set()
        for name in self._all_names():
            if name in seen:
                duplicates.add(name)
            seen.add(name)
        if duplicates:
            raise ValueError(f"Duplicate names: {duplicates}")
        return self

    @model_validator(mode="after")
    def check_input_references(self):
        valid = self._valid_input_names()
        for c in self.units:
            for ref in _get_input_names(c):
                if ref not in valid:
                    raise ValueError(f"'{c.name}' has INPUT '{ref}' which is not a known source or provider.")
        return self

    @model_validator(mode="after")
    def check_no_cycles(self):
        from graphlib import CycleError, TopologicalSorter

        graph: dict[str, set[str]] = {c.name: set(_get_input_names(c)) for c in self.units}
        try:
            tuple(TopologicalSorter(graph).static_order())
        except CycleError as e:
            raise ValueError(f"Cycle detected in energy network: {e}") from None
        return self

    @model_validator(mode="after")
    def check_energy_type_compatibility(self):
        output_types: dict[str, EnergyType] = {}
        for s in self.sources:
            output_types[s.name] = SOURCE_OUTPUT_ENERGY[s.type]
        for c in self.units:
            if c.type in OUTPUT_ENERGY:
                output_types[c.name] = OUTPUT_ENERGY[c.type]

        for c in self.units:
            if c.type in INPUT_ENERGY_ALTERNATIVES:
                allowed_inputs = INPUT_ENERGY_ALTERNATIVES[c.type]
                for ref in _get_input_names(c):
                    provided = output_types.get(ref)
                    if provided is not None and provided not in allowed_inputs:
                        raise ValueError(
                            f"'{c.name}' ({c.type}) expects one of {allowed_inputs} input, "
                            f"but '{ref}' provides {provided}."
                        )
                continue
            if c.type not in INPUT_ENERGY:
                raise ValueError(f"'{c.name}': unknown component type '{c.type}' — not in energy type map.")
            expected_input = INPUT_ENERGY[c.type]
            for ref in _get_input_names(c):
                provided = output_types.get(ref)
                if provided is not None and provided != expected_input:
                    raise ValueError(
                        f"'{c.name}' ({c.type}) expects {expected_input} input, but '{ref}' provides {provided}."
                    )
        return self
