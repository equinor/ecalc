from libecalc.domain.process.process_system.process_unit import ProcessUnit
from libecalc.domain.process.value_objects.fluid_stream import FluidService, FluidStream


class Choke(ProcessUnit):
    def __init__(
        self,
        fluid_service: FluidService,
        target_pressure: float | None = None,
    ):
        self._target_pressure = target_pressure
        self._fluid_service = fluid_service

    def set_target_pressure(self, target_pressure: float) -> None:
        self._target_pressure = target_pressure

    def propagate_stream(self, inlet_stream: FluidStream) -> FluidStream | None:
        if self._target_pressure is None:
            # Delta pressure = 0, i.e. don't do anything
            return inlet_stream

        return self._fluid_service.create_stream_from_standard_rate(
            fluid_model=inlet_stream.fluid_model,
            pressure_bara=self._target_pressure,
            temperature_kelvin=inlet_stream.pressure_bara,
            standard_rate_m3_per_day=inlet_stream.standard_rate_sm3_per_day,
        )
