from enum import StrEnum
from typing import Annotated

from pydantic import ConfigDict, Field, model_validator

from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.energy.yaml_sources import YamlEnergySource
from libecalc.presentation.yaml.yaml_types.energy.yaml_units import YamlEnergyNetworkUnit


class EnergyType(StrEnum):
    FUEL_GAS = "FUEL_GAS"
    ELECTRICAL = "ELECTRICAL"
    MECHANICAL = "MECHANICAL"
    DIESEL = "DIESEL"


INPUT_ENERGY_TYPE_BY_UNIT_TYPE: dict[str, EnergyType] = {
    "GENERATOR_SET": EnergyType.FUEL_GAS,
    "GAS_TURBINE": EnergyType.FUEL_GAS,
    "ELECTRICAL_MOTOR": EnergyType.ELECTRICAL,
    "ELECTRICAL_CABLE": EnergyType.ELECTRICAL,
    "ELECTRICAL_BUS": EnergyType.ELECTRICAL,
    "FUEL_GAS_MANIFOLD": EnergyType.FUEL_GAS,
    "ELECTRICAL_CONSUMER": EnergyType.ELECTRICAL,
    "COMPRESSOR": EnergyType.MECHANICAL,
    "PUMP": EnergyType.MECHANICAL,
    "FUEL_GAS_CONSUMER": EnergyType.FUEL_GAS,
    "DIESEL_CONSUMER": EnergyType.DIESEL,
}

OUTPUT_ENERGY_TYPE_BY_NODE_TYPE: dict[str, EnergyType] = {
    "FUEL_GAS_SOURCE": EnergyType.FUEL_GAS,
    "DIESEL_SOURCE": EnergyType.DIESEL,
    "ONSHORE_GRID": EnergyType.ELECTRICAL,
    "OFFSHORE_WIND": EnergyType.ELECTRICAL,
    "GENERATOR_SET": EnergyType.ELECTRICAL,
    "GAS_TURBINE": EnergyType.MECHANICAL,
    "ELECTRICAL_MOTOR": EnergyType.MECHANICAL,
    "ELECTRICAL_CABLE": EnergyType.ELECTRICAL,
    "ELECTRICAL_BUS": EnergyType.ELECTRICAL,
    "FUEL_GAS_MANIFOLD": EnergyType.FUEL_GAS,
}

CONSUMER_TYPES = set(INPUT_ENERGY_TYPE_BY_UNIT_TYPE) - set(OUTPUT_ENERGY_TYPE_BY_NODE_TYPE)


def _get_input_names(component: YamlEnergyNetworkUnit) -> list[str]:
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
        list[YamlEnergyNetworkUnit],
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
        for source in self.sources:
            output_types[source.name] = OUTPUT_ENERGY_TYPE_BY_NODE_TYPE[source.type]
        for c in self.units:
            if c.type in OUTPUT_ENERGY_TYPE_BY_NODE_TYPE:
                output_types[c.name] = OUTPUT_ENERGY_TYPE_BY_NODE_TYPE[c.type]

        for c in self.units:
            if c.type not in INPUT_ENERGY_TYPE_BY_UNIT_TYPE:
                raise ValueError(f"'{c.name}': unknown component type '{c.type}' — not in energy type map.")
            expected_inputs = INPUT_ENERGY_TYPE_BY_UNIT_TYPE[c.type]
            for ref in _get_input_names(c):
                provided = output_types.get(ref)
                if provided is not None and provided != expected_inputs:
                    raise ValueError(
                        f"'{c.name}' ({c.type}) expects {expected_inputs} input, but '{ref}' provides {provided}."
                    )
        return self
