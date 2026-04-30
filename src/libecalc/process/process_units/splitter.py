from typing import Final

from libecalc.process.fluid_stream.fluid_service import FluidService
from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.process_pipeline.process_unit import ProcessUnit, ProcessUnitId


class Splitter(ProcessUnit):
    """Removes a fixed standard rate from the through-stream.

    The split rate is set via `set_rate` before propagation. This models a gas
    offtake point (e.g. fuel gas) in an interstage manifold. The remainder
    continues downstream.
    """

    def __init__(self, fluid_service: FluidService, process_unit_id: ProcessUnitId | None = None, rate: float = 0.0):
        self._id: Final[ProcessUnitId] = process_unit_id or ProcessUnit._create_id()
        self._fluid_service = fluid_service
        self._rate = rate

    def get_id(self) -> ProcessUnitId:
        return self._id

    def set_rate(self, rate: float) -> None:
        self._rate = rate

    def get_rate(self) -> float:
        return self._rate

    def propagate_stream(self, inlet_stream: FluidStream) -> FluidStream:
        remaining_rate = inlet_stream.standard_rate_sm3_per_day - self._rate
        return self._fluid_service.create_stream_from_standard_rate(
            fluid_model=inlet_stream.fluid_model,
            pressure_bara=inlet_stream.pressure_bara,
            temperature_kelvin=inlet_stream.temperature_kelvin,
            standard_rate_m3_per_day=remaining_rate,
        )

    def get_split_stream(self, inlet_stream: FluidStream) -> FluidStream:
        """Return the stream that was split off, at the same conditions as the inlet."""
        return self._fluid_service.create_stream_from_standard_rate(
            fluid_model=inlet_stream.fluid_model,
            pressure_bara=inlet_stream.pressure_bara,
            temperature_kelvin=inlet_stream.temperature_kelvin,
            standard_rate_m3_per_day=self._rate,
        )
