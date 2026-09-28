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


class YamlJunctionInput(YamlBase):
    model_config = ConfigDict(title="JunctionInput")

    name: Annotated[
        str,
        Field(
            title="NAME",
            description="Source or unit feeding into this junction.",
        ),
    ]
    capacity: Annotated[
        YamlExpressionType | None,
        Field(
            title="CAPACITY",
            description=(
                "Dispatch limit for this input, measured at the junction after any upstream loss. It guides how "
                "demand is split and does not cap it: demand beyond every limit is placed on the last input, and "
                "exceeding a limit is not itself a capacity failure. Omit for unlimited, until a deliverability "
                "rule exists."
            ),
        ),
    ] = None

    @field_validator("capacity", mode="after")
    @classmethod
    def _capacity_non_negative(cls, v: YamlExpressionType | None) -> YamlExpressionType | None:
        return _check_non_negative(v, "CAPACITY")


class YamlJunctionBase(YamlBase):
    name: Annotated[
        str,
        Field(
            title="NAME",
            description="Unique name for this component.",
        ),
    ]
    input: Annotated[
        list[str | YamlJunctionInput],
        Field(
            title="INPUT",
            description=(
                "At least two sources or units feeding into this junction, in dispatch priority order. An entry is "
                "either a name, or a NAME with an optional CAPACITY dispatch limit. A single supplier connects "
                "directly to its consumers instead."
            ),
            min_length=2,
        ),
    ]
    dispatch_strategy: Annotated[
        YamlDispatchStrategy,
        Field(
            title="DISPATCH_STRATEGY",
            description="How to allocate demand across the inputs.",
        ),
    ]

    def get_inputs(self) -> list[YamlJunctionInput]:
        """Normalize inputs to objects, preserving declared priority order."""
        return [YamlJunctionInput(name=entry) if isinstance(entry, str) else entry for entry in self.input]

    @model_validator(mode="after")
    def check_dispatch_strategy_supported(self):
        # EQUAL_SPLIT is reserved in the schema but has no domain implementation yet.
        if self.dispatch_strategy == YamlDispatchStrategy.EQUAL_SPLIT:
            raise ValueError(f"'{self.name}': DISPATCH_STRATEGY {self.dispatch_strategy} is not supported yet.")
        return self

    @model_validator(mode="after")
    def check_no_duplicate_inputs(self):
        names = [junction_input.name for junction_input in self.get_inputs()]
        if len(names) != len(set(names)):
            duplicates = [ref for ref in names if names.count(ref) > 1]
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


class YamlCompressorSampled(YamlConsumerBase):
    """
    A compressor whose energy usage is tabulated in `FILE` against `RATE`, `SUCTION_PRESSURE` and/or
    `DISCHARGE_PRESSURE`. Which energy columns `FILE` has decides what the unit consumes:

    - Only `FUEL`: a fuel gas consumer. `INPUT` must provide fuel gas.
    - Only `POWER`: a power consumer, electrical or mechanical after what `INPUT` provides.
    - Both `FUEL` and `POWER`: a gas turbine named `<NAME> turbine` is generated and wired between `INPUT`
      (which must provide fuel gas) and the compressor. The compressor demands the tabulated `POWER` as
      shaft power and the turbine converts it back to the tabulated `FUEL`.

    Every variable tabulated in `FILE` must be given as an expression, and every given expression must be
    tabulated.
    """

    model_config = ConfigDict(title="CompressorSampled")

    type: Literal["COMPRESSOR_SAMPLED"]
    file: Annotated[
        str,
        Field(
            title="FILE",
            description="Resource tabulating FUEL and/or POWER against RATE, SUCTION_PRESSURE and/or "
            "DISCHARGE_PRESSURE.",
        ),
    ]
    rate: Annotated[
        YamlExpressionType | None,
        Field(
            title="RATE",
            description="Rate through the compressor (Sm³/d), looked up in FILE.",
        ),
    ] = None
    suction_pressure: Annotated[
        YamlExpressionType | None,
        Field(
            title="SUCTION_PRESSURE",
            description="Compressor inlet pressure (bara), looked up in FILE.",
        ),
    ] = None
    discharge_pressure: Annotated[
        YamlExpressionType | None,
        Field(
            title="DISCHARGE_PRESSURE",
            description="Compressor outlet pressure (bara), looked up in FILE.",
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
        if self.rate is None and self.suction_pressure is None and self.discharge_pressure is None:
            raise ValueError(
                f"'{self.name}': at least one of RATE, SUCTION_PRESSURE or DISCHARGE_PRESSURE is required."
            )
        return self


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
        YamlCompressorSampled,
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

FILE_DEFINED_INPUT_TYPES = {"COMPRESSOR_SAMPLED"}

CONSUMER_TYPES = (set(INPUT_ENERGY) - set(OUTPUT_ENERGY)) | FILE_DEFINED_INPUT_TYPES


def get_input_names(component: YamlComponent) -> list[str]:
    """Return input names in declared order."""
    if isinstance(component, YamlJunctionBase):
        return [junction_input.name for junction_input in component.get_inputs()]
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
            for ref in get_input_names(c):
                if ref not in valid:
                    raise ValueError(f"'{c.name}' has INPUT '{ref}' which is not a known source or provider.")
        return self

    @model_validator(mode="after")
    def check_no_cycles(self):
        from graphlib import CycleError, TopologicalSorter

        graph: dict[str, set[str]] = {c.name: set(get_input_names(c)) for c in self.units}
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
            if c.type in FILE_DEFINED_INPUT_TYPES:
                continue
            if c.type not in INPUT_ENERGY:
                raise ValueError(f"'{c.name}': unknown component type '{c.type}' — not in energy type map.")
            expected_input = INPUT_ENERGY[c.type]
            for ref in get_input_names(c):
                provided = output_types.get(ref)
                if provided is not None and provided != expected_input:
                    raise ValueError(
                        f"'{c.name}' ({c.type}) expects {expected_input} input, but '{ref}' provides {provided}."
                    )
        return self
