from datetime import datetime
from functools import reduce
from typing import List, Literal, Optional

from libecalc.common.logger import logger
from libecalc.common.string_utils import to_camel_case
from libecalc.common.utils.rates import TimeSeriesFloat, TimeSeriesStreamDayRate
from pydantic import BaseModel, Extra
from typing_extensions import Self


class Stream(BaseModel):
    class Config:
        extra = Extra.forbid
        alias_generator = to_camel_case
        allow_population_by_field_name = True

    name: Optional[str]
    rate: TimeSeriesStreamDayRate
    pressure: TimeSeriesFloat
    fluid_density: Optional[TimeSeriesFloat] = None

    def mix(self, other_stream: "Stream") -> "Stream":
        """
        Mix two streams. This needs to be expanded to handle fluids (density, composition, etc.).

        Assuming 'self' sets the target pressure.
        Args:
            other_stream: The stream to be mixed in.

        Returns: The mixed stream

        """
        target_pressure = self.pressure  # Assuming 'self' decides the target pressure
        if other_stream.pressure < target_pressure:
            # TODO: return a warning object with the specific timesteps?
            logger.warning("Increasing pressure when mixing stream. That should not happen.")
        else:
            return Stream(
                rate=self.rate + other_stream.rate,
                pressure=target_pressure,
                fluid_density=self.fluid_density,  # Check that they are equal? Or handle it?
            )

    def get_subset_for_timestep(self, current_timestep: datetime) -> Self:
        """
        For a given timestep, get the stream that is relevant for that timestep only.

        Args:
            current_timestep: the timestep must be a part of the global timevector

        Returns: the stream that is relevant for the given timestep.

        """
        return Stream(
            rate=self.rate.for_timestep(current_timestep),
            pressure=self.pressure.for_timestep(current_timestep),
            fluid_density=self.fluid_density.for_timestep(current_timestep) if self.fluid_density is not None else None,
        )

    @classmethod
    def mix_all(cls, streams: List["Stream"]) -> "Stream":
        if len(streams) == 0:
            raise ValueError("No streams to mix")
        return reduce(Stream.mix, streams)


class Stage(BaseModel):
    class Config:
        extra = Extra.forbid
        alias_generator = to_camel_case
        allow_population_by_field_name = True

    name: Literal["inlet", "before_choke", "outlet"]
    stream: Stream
