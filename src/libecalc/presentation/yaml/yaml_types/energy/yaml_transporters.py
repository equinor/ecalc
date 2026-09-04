from typing import Annotated, Literal

from pydantic import ConfigDict, Field, field_validator

from libecalc.presentation.yaml.yaml_types.components.yaml_expression_type import YamlExpressionType
from libecalc.presentation.yaml.yaml_types.energy.yaml_energy_common import (
    YamlEnergyNetworkNodeBase,
    _check_efficiency,
    _check_non_negative,
)


class YamlTransporterBase(YamlEnergyNetworkNodeBase):
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


class YamlElectricalCable(YamlTransporterBase):
    model_config = ConfigDict(title="ElectricalCable")

    type: Literal["ELECTRICAL_CABLE"]
    efficiency: Annotated[
        YamlExpressionType,
        Field(
            title="EFFICIENCY",
            description="Transmission efficiency (0–1]. 1.0 means no loss. Defaults to 1.0 if omitted.",
        ),
    ] = 1.0

    @field_validator("efficiency", mode="after")
    @classmethod
    def _efficiency_in_range(cls, v: YamlExpressionType | None) -> YamlExpressionType | None:
        return _check_efficiency(v)
