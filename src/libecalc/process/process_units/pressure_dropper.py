from typing import Final

from libecalc.process.fluid_stream.fluid_service import FluidService
from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.process_pipeline.process_error import InsufficientInletPressureError
from libecalc.process.process_pipeline.process_unit import ProcessUnit, ProcessUnitId


class PressureDropper(ProcessUnit):
    def __init__(
        self,
        fluid_service: FluidService,
        process_unit_id: ProcessUnitId | None = None,
        pressure_drop_bara: float = 0.0,
    ):
        self._id: Final[ProcessUnitId] = process_unit_id or ProcessUnit._create_id()
        self._pressure_drop_bara = pressure_drop_bara
        self._fluid_service = fluid_service

    def get_id(self) -> ProcessUnitId:
        return self._id

    @property
    def pressure_drop(self) -> float:
        return self._pressure_drop_bara

    def set_pressure_drop(self, pressure_drop_bara: float) -> None:
        if pressure_drop_bara < 0:
            raise ValueError("Pressure drop cannot be negative")
        self._pressure_drop_bara = pressure_drop_bara

    def propagate_stream(self, inlet_stream: FluidStream) -> FluidStream:
        if self._pressure_drop_bara > 0.0:
            new_pressure_bara = inlet_stream.pressure_bara - self._pressure_drop_bara
            if new_pressure_bara < 0.0:
                raise InsufficientInletPressureError(
                    process_unit_id=self._id,
                    inlet_pressure_bara=inlet_stream.pressure_bara,
                    required_delta_pressure_bara=self._pressure_drop_bara,
                )
        else:
            # Delta pressure = 0, i.e. don't do anything
            return inlet_stream

        return self._fluid_service.create_stream_from_standard_rate(
            fluid_model=inlet_stream.fluid_model,
            pressure_bara=new_pressure_bara,
            temperature_kelvin=inlet_stream.temperature_kelvin,
            standard_rate_m3_per_day=inlet_stream.standard_rate_sm3_per_day,
        )
