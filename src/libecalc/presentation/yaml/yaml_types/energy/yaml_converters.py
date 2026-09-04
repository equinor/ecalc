from typing import Annotated, Literal

from pydantic import ConfigDict, Field, field_validator

from libecalc.presentation.yaml.yaml_types.components.yaml_expression_type import YamlExpressionType
from libecalc.presentation.yaml.yaml_types.energy.yaml_energy_common import (
    YamlEnergyNetworkNodeBase,
    _check_efficiency,
    _check_non_negative,
)


class YamlConverterBase(YamlEnergyNetworkNodeBase):
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
        str,
        Field(
            title="MODEL",
            description="Reference to a facility model defining the power-to-fuel curve.",
        ),
    ]


class YamlGasTurbine(YamlConverterBase):
    model_config = ConfigDict(title="GasTurbine")

    type: Literal["GAS_TURBINE"]
    model: Annotated[
        str,
        Field(
            title="MODEL",
            description="Reference to a facility model defining the power-to-fuel curve.",
        ),
    ]


class YamlElectricalMotor(YamlConverterBase):
    model_config = ConfigDict(title="ElectricalMotor")

    type: Literal["ELECTRICAL_MOTOR"]
    efficiency: Annotated[
        YamlExpressionType,
        Field(
            title="EFFICIENCY",
            description="Conversion efficiency (0–1]. Defaults to 0.95 if omitted.",
        ),
    ] = 0.95

    @field_validator("efficiency", mode="after")
    @classmethod
    def _efficiency_in_range(cls, v: YamlExpressionType | None) -> YamlExpressionType | None:
        return _check_efficiency(v)
