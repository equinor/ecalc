import operator
from datetime import datetime
from functools import reduce
from typing import List, Optional

from pydantic import BaseModel, ConfigDict

from libecalc.common.string.string_utils import generate_id, to_camel_case
from libecalc.common.utils.rates import TimeSeriesFloat, TimeSeriesStreamDayRate
from libecalc.domain.stream_conditions import (
    Density,
    Pressure,
    Rate,  # TODO: import from domain, domain also imports from common
    StreamConditions,
    Temperature,
)


class TimeSeriesStreamConditions(BaseModel):
    model_config = ConfigDict(extra="forbid", alias_generator=to_camel_case, populate_by_name=True)

    id: str
    name: str
    rate: Optional[TimeSeriesStreamDayRate] = None
    pressure: Optional[TimeSeriesFloat] = None
    temperature: Optional[TimeSeriesFloat] = None
    fluid_density: Optional[TimeSeriesFloat] = None

    def mix(self, *other_streams: "TimeSeriesStreamConditions") -> "TimeSeriesStreamConditions":
        """
        Mix two streams. This needs to be expanded to handle fluids (density, composition, etc.).

        Assuming 'self' sets the target pressure.
        Args:
            other_streams: The streams to be mixed in.

        Returns: The mixed stream

        """
        streams = [self, *other_streams]
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
        if any(stream.pressure < target_pressure for stream in other_streams):  # type: ignore
            # TODO: return a warning object with the specific timesteps?
            raise ValueError("Increasing pressure when mixing streams. That should not happen.")

        return TimeSeriesStreamConditions(
            id=generate_id(*[stream.id for stream in streams]),
            name=f"{'-'.join(stream.name for stream in streams)}",
            rate=reduce(operator.add, [stream.rate for stream in streams]),
            pressure=target_pressure,
            fluid_density=self.fluid_density,  # TODO: Check that they are equal? Or handle it?
        )

    def for_timestep(self, current_timestep: datetime) -> StreamConditions:
        """
        For a given timestep, get the stream that is relevant for that timestep only.

        Args:
            current_timestep: the timestep must be a part of the global timevector

        Returns: the stream that is relevant for the given timestep.

        """
        return StreamConditions(
            id=self.id,
            name=self.name,
            timestep=current_timestep,
            rate=Rate(value=self.rate.for_timestep(current_timestep).values[0], unit=self.rate.unit)
            if self.rate is not None
            else None,
            pressure=Pressure(value=self.pressure.for_timestep(current_timestep).values[0], unit=self.pressure.unit)
            if self.pressure is not None
            else None,
            density=Density(
                value=self.fluid_density.for_timestep(current_timestep).values[0], unit=self.fluid_density.unit
            )
            if self.fluid_density is not None
            else None,
            temperature=Temperature(
                value=self.temperature.for_timestep(current_timestep).values[0], unit=self.temperature.unit
            )
            if self.temperature is not None
            else None,
        )

    @classmethod
    def from_stream_condition(cls, stream_conditions: StreamConditions) -> "TimeSeriesStreamConditions":
        return TimeSeriesStreamConditions(
            id=stream_conditions.id,
            name=stream_conditions.name,
            rate=TimeSeriesStreamDayRate(
                timesteps=[stream_conditions.timestep],
                values=[stream_conditions.rate.value],
                unit=stream_conditions.rate.unit,
            ),
            pressure=TimeSeriesFloat(
                timesteps=[stream_conditions.timestep],
                values=[stream_conditions.pressure.value],
                unit=stream_conditions.pressure.unit,
            ),
            temperature=TimeSeriesFloat(
                timesteps=[stream_conditions.timestep],
                values=[stream_conditions.temperature.value],
                unit=stream_conditions.temperature.unit,
            )
            if stream_conditions.temperature is not None
            else None,
            fluid_density=TimeSeriesFloat(
                timesteps=[stream_conditions.timestep],
                values=[stream_conditions.density.value],
                unit=stream_conditions.density.unit,
            )
            if stream_conditions.density is not None
            else None,
        )

    @classmethod
    def mix_all(cls, streams: List["TimeSeriesStreamConditions"]) -> "TimeSeriesStreamConditions":
        if len(streams) == 0:
            raise ValueError("No streams to mix")
        if len(streams) == 1:
            return streams[0].model_copy()

        first, *rest = streams
        return first.model_copy().mix(*rest)
