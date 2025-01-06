from __future__ import annotations

from typing import Optional

from libecalc.common.units import Unit
from libecalc.common.utils.rates import RateType
from libecalc.dto.utils.validators import ExpressionType


class ExpressionTimeSeries:
    def __init__(self, value: ExpressionType, unit: Unit, type: Optional[RateType] = None):
        self.value = value
        self.unit = unit
        self.type = type


class ExpressionStreamConditions:
    def __init__(
        self,
        rate: Optional[ExpressionTimeSeries] = None,
        pressure: Optional[ExpressionTimeSeries] = None,
        temperature: Optional[ExpressionTimeSeries] = None,
        fluid_density: Optional[ExpressionTimeSeries] = None,
    ):
        self.rate = rate
        self.pressure = pressure
        self.temperature = temperature
        self.fluid_density = fluid_density


ConsumerID = str
PriorityID = str
StreamID = str

SystemStreamConditions = dict[ConsumerID, dict[StreamID, ExpressionStreamConditions]]


class Crossover:
    def __init__(self, from_component_id: str, to_component_id: str, stream_name: Optional[str] = None):
        self.stream_name = stream_name
        self.from_component_id = from_component_id
        self.to_component_id = to_component_id


class SystemComponentConditions:
    def __init__(self, crossover: list[Crossover]):
        self.crossover = crossover
