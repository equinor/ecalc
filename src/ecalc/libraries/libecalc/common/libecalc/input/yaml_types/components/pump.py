from typing import Optional

from libecalc.expression import Expression
from libecalc.input.yaml_types.components.base import (
    ConsumerBase,
    OperationalConditionBase,
)
from libecalc.input.yaml_types.temporal_model import TemporalModel
from pydantic import Field


class OperationalSettings(OperationalConditionBase):
    fluid_density: Optional[Expression]
    rate: Optional[Expression]
    inlet_pressure: Optional[Expression]
    outlet_pressure: Optional[Expression]


class Pump(ConsumerBase):
    category: Optional[str] = Field(
        None,
        title="CATEGORY",
        description="User defined category",
    )
    energy_usage_model: TemporalModel[str]


class PumpStage(Pump):
    user_defined_category: str
    operational_settings: OperationalSettings
