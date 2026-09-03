from typing import Annotated, Literal

from pydantic import Field, field_validator

from libecalc.presentation.yaml.yaml_types.components.yaml_expression_type import YamlExpressionType
from libecalc.presentation.yaml.yaml_types.energy.yaml_energy_common import (
    YamlEnergyNetworkNodeBase,
    _check_non_negative,
)


class YamlEnergySourceBase(YamlEnergyNetworkNodeBase):
    capacity: Annotated[
        YamlExpressionType | None,
        Field(
            title="CAPACITY",
            description="Maximum output capacity. Omit for unlimited.",
        ),
    ] = None

    @field_validator("capacity", mode="after")
    @classmethod
    def _capacity_non_negative(
        cls,
        value: YamlExpressionType | None,
    ) -> YamlExpressionType | None:
        return _check_non_negative(value, "CAPACITY")


class YamlFuelGasSource(YamlEnergySourceBase):
    type: Literal["FUEL_GAS_SOURCE"]


class YamlDieselSource(YamlEnergySourceBase):
    type: Literal["DIESEL_SOURCE"]


class YamlOnshoreGrid(YamlEnergySourceBase):
    type: Literal["ONSHORE_GRID"]


class YamlOffshoreWind(YamlEnergySourceBase):
    type: Literal["OFFSHORE_WIND"]


YamlEnergySource = Annotated[
    YamlFuelGasSource | YamlDieselSource | YamlOnshoreGrid | YamlOffshoreWind,
    Field(discriminator="type"),
]
