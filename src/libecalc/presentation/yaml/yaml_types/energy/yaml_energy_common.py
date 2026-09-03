from typing import Annotated

from pydantic import ConfigDict, Field

from libecalc.energy.energy_use import EnergyUse
from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.components.yaml_expression_type import YamlExpressionType


def _check_non_negative(v: YamlExpressionType | None, field_name: str) -> YamlExpressionType | None:
    if isinstance(v, (int, float)) and v < 0:
        raise ValueError(f"{field_name} must be non-negative, got {v}")
    return v


def _check_efficiency(v: YamlExpressionType | None) -> YamlExpressionType | None:
    if isinstance(v, (int, float)) and not (0 < v <= 1):
        raise ValueError(f"EFFICIENCY must be in (0, 1], got {v}")
    return v


class YamlEnergyUnitMetadata(YamlBase):
    model_config = ConfigDict(title="EnergyUnitMetadata")

    energy_use: Annotated[
        EnergyUse | None,
        Field(
            title="ENERGY_USE",
            description="Controlled classification for analysis. Does not affect calculations.",
        ),
    ] = None


class YamlEnergyNetworkNodeBase(YamlBase):
    name: Annotated[
        str,
        Field(
            title="NAME",
            description="Unique name for this energy network node.",
        ),
    ]
    metadata: Annotated[
        YamlEnergyUnitMetadata | None,
        Field(
            title="METADATA",
            description="Optional metadata for classification and analysis.",
        ),
    ] = None
