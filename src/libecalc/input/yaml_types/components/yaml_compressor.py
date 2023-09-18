from typing import Optional, Union

from libecalc.expression import Expression
from libecalc.input.yaml_types.components.yaml_base import (
    YamlConsumerBase,
    YamlOperationalConditionBase,
)
from libecalc.input.yaml_types.models import YamlCompressorWithTurbine
from libecalc.input.yaml_types.yaml_temporal_model import YamlTemporalModel
from pydantic import Field

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
