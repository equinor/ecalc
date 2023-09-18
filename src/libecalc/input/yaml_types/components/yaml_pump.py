from typing import Optional

from libecalc.expression import Expression
from libecalc.input.yaml_types.components.yaml_base import (
    YamlConsumerBase,
    YamlOperationalConditionBase,
)
from libecalc.input.yaml_types.yaml_temporal_model import YamlTemporalModel
from pydantic import Field


class YamlPumpOperationalSettings(YamlOperationalConditionBase):
    class Config:
        title = "PumpOperationalSettings"

    fluid_density: Optional[Expression]
    rate: Optional[Expression]
    inlet_pressure: Optional[Expression]
    outlet_pressure: Optional[Expression]


class YamlPump(YamlConsumerBase):
    class Config:
        title = "Pump"

    category: Optional[str] = Field(
        None,
        title="CATEGORY",
        description="User defined category",
    )
    energy_usage_model: YamlTemporalModel[str]


class YamlPumpStage(YamlPump):
    class Config:
        title = "PumpStage"

    user_defined_category: str
    operational_settings: YamlPumpOperationalSettings
