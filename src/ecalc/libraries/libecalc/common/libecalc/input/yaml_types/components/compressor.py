from typing import Optional, Union

from libecalc.expression import Expression
from libecalc.input.yaml_types.components.base import (
    ConsumerBase,
    OperationalConditionBase,
)
from libecalc.input.yaml_types.models import CompressorWithTurbine
from libecalc.input.yaml_types.temporal_model import TemporalModel
from pydantic import Field

CompressorModel = Union[CompressorWithTurbine]


class OperationalSettings(OperationalConditionBase):
    rate: Optional[Expression]
    inlet_pressure: Optional[Expression]
    outlet_pressure: Optional[Expression]


class Compressor(ConsumerBase):
    category: Optional[str] = Field(
        None,
        title="CATEGORY",
        description="User defined category",
    )
    energy_usage_model: TemporalModel[str]


class CompressorStage(Compressor):
    user_defined_category: str
    operational_settings: OperationalSettings
