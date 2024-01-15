"""
Point in time stream conditions
"""
from __future__ import annotations

import dataclasses
import operator
from dataclasses import dataclass
from datetime import datetime
from functools import reduce
from typing import Dict, List

from libecalc.common.string.string_utils import generate_id
from libecalc.common.units import Unit


@dataclass
class Pressure:
    value: float
    unit: Unit

    def __lt__(self, other: Pressure) -> bool:
        if self.unit != other.unit:
            raise ValueError("Unit mismatch")

        return self.value < other.value


@dataclass
class Rate:
    value: float
    unit: Unit

    def __add__(self, other) -> Rate:
        if self.unit != other.unit:
            raise ValueError("Unit mismatch")

        return Rate(
            value=self.value + other.value,
            unit=self.unit,
        )


@dataclass
class Density:
    value: float
    unit: Unit


@dataclass
class Temperature:
    value: float
    unit: Unit


@dataclass
class StreamConditions:
    id: str
    name: str
    timestep: datetime
    rate: Rate
    pressure: Pressure
    density: Density = None
    temperature: Temperature = None

    def mix(self, *other_stream_conditions: StreamConditions) -> StreamConditions:
        streams = [self, *other_stream_conditions]
        if any(stream.rate is None for stream in streams):
            streams_with_undefined_rate = [stream.name for stream in streams if stream.rate is None]
            raise ValueError(
                f"Mixing streams {', '.join(stream.name for stream in streams)} where {', '.join(streams_with_undefined_rate)} does not have a rate."
            )

        if any(stream.pressure is None for stream in streams):
            streams_with_undefined_pressure = [stream.name for stream in streams if stream.pressure is None]
            raise ValueError(
                f"Mixing streams {', '.join(stream.name for stream in streams)} where {', '.join(streams_with_undefined_pressure)} does not have a pressure."
            )

        target_pressure = self.pressure  # Assuming 'self' decides the target pressure
        if any(stream.pressure < target_pressure for stream in other_stream_conditions):
            raise ValueError("Increasing pressure when mixing streams. That should not happen.")

        target_temperature = self.temperature  # Assuming 'self' decides the target temperature
        if target_temperature is not None and any(
            stream.temperature == target_temperature for stream in other_stream_conditions
        ):
            raise ValueError("Changing temperature when mixing streams. That should not happen.")

        return StreamConditions(
            id=generate_id(*[stream.id for stream in streams]),
            name=f"{'-'.join(stream.name for stream in streams)}",
            timestep=self.timestep,
            rate=reduce(operator.add, [stream.rate for stream in streams]),
            pressure=target_pressure,
            density=self.density,  # TODO: Check that they are equal? Or handle it?
            temperature=self.temperature,
        )

    def copy(self, update: Dict = None):
        if update is None:
            update = {}

        return dataclasses.replace(self, **update)

    @classmethod
    def mix_all(cls, streams: List[StreamConditions]) -> StreamConditions:
        if len(streams) == 0:
            raise ValueError("No streams to mix")
        if len(streams) == 1:
            return streams[0].copy()

        first, *rest = streams
        return first.copy().mix(*rest)
