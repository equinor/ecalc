import operator
from datetime import datetime
from functools import reduce
from typing import List, Literal, Optional

from libecalc.common.string_utils import to_camel_case
from libecalc.common.utils.rates import TimeSeriesFloat, TimeSeriesStreamDayRate
from pydantic import BaseModel, Extra
from typing_extensions import Self


class Stream(BaseModel):
    class Config:
        extra = Extra.forbid
        alias_generator = to_camel_case
        allow_population_by_field_name = True

    name: str
    rate: Optional[TimeSeriesStreamDayRate]
    pressure: Optional[TimeSeriesFloat]
    fluid_density: Optional[TimeSeriesFloat] = None

    def mix(self, *other_streams: "Stream") -> "Stream":
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

        return Stream(
            name=f"Mixed-{'-'.join(stream.name for stream in streams)}",
            rate=reduce(operator.add, [stream.rate for stream in streams]),
            pressure=target_pressure,
            fluid_density=self.fluid_density,  # TODO: Check that they are equal? Or handle it?
        )

    def get_subset_for_timestep(self, current_timestep: datetime) -> Self:
        """
        For a given timestep, get the stream that is relevant for that timestep only.

        Args:
            current_timestep: the timestep must be a part of the global timevector

        Returns: the stream that is relevant for the given timestep.

        """
        return Stream(
            name=self.name,
            rate=self.rate.for_timestep(current_timestep) if self.rate is not None else None,
            pressure=self.pressure.for_timestep(current_timestep) if self.pressure is not None else None,
            fluid_density=self.fluid_density.for_timestep(current_timestep) if self.fluid_density is not None else None,
        )

    @classmethod
    def mix_all(cls, streams: List["Stream"]) -> "Stream":
        if len(streams) == 0:
            raise ValueError("No streams to mix")
        if len(streams) == 1:
            return streams[0].copy()

        first, *rest = streams
        return first.copy().mix(*rest)


class Stage(BaseModel):
    class Config:
        extra = Extra.forbid
        alias_generator = to_camel_case
        allow_population_by_field_name = True

    name: Literal["inlet", "before_choke", "outlet"]
    stream: Stream
