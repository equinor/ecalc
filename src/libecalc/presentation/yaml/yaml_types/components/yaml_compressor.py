from typing import Literal, Optional, Union

from pydantic import Field

from libecalc.dto.base import ComponentType
from libecalc.expression import Expression
from libecalc.presentation.yaml.yaml_types.components.yaml_base import (
    YamlConsumerBase,
    YamlOperationalConditionBase,
)
from libecalc.presentation.yaml.yaml_types.models import YamlCompressorWithTurbine
from libecalc.presentation.yaml.yaml_types.yaml_temporal_model import YamlTemporalModel

CompressorModel = Union[YamlCompressorWithTurbine]


class YamlCompressorOperationalSettings(YamlOperationalConditionBase):
    class Config:
        title = "CompressorOperationalSettings"

    rate: Optional[Expression]
    inlet_pressure: Optional[Expression]
    outlet_pressure: Optional[Expression]


class YamlCompressor(YamlConsumerBase):
    class Config:
        title = "Compressor"

    component_type: Literal[ComponentType.COMPRESSOR_V2] = Field(
        ...,
        title="TYPE",
        description="The type of the component",
        alias="TYPE",
    )

    category: Optional[str] = Field(
        None,
        title="CATEGORY",
        description="User defined category",
    )
    energy_usage_model: YamlTemporalModel[str]


class YamlCompressorStage(YamlCompressor):
    class Config:
        title = "CompressorStage"

    user_defined_category: str
    operational_settings: YamlCompressorOperationalSettings
