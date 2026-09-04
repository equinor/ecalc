from typing import Annotated, Literal

from pydantic import ConfigDict, Field, model_validator

from libecalc.energy.energy_units.junction import DispatchStrategy
from libecalc.presentation.yaml.yaml_types.energy.yaml_energy_common import YamlEnergyNetworkNodeBase


class YamlJunctionBase(YamlEnergyNetworkNodeBase):
    input: Annotated[
        list[str],
        Field(
            title="INPUT",
            description="Sources or units feeding into this junction.",
        ),
    ]
    dispatch_strategy: Annotated[
        DispatchStrategy | None,
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
