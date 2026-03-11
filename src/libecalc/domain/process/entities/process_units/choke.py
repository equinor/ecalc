from dataclasses import dataclass

from libecalc.domain.process.process_system.process_error import OutsideCapacityError
from libecalc.domain.process.process_system.process_unit import ProcessUnit, ProcessUnitId, ProcessUnitProperties
from libecalc.domain.process.value_objects.fluid_stream import FluidService, FluidStream

@dataclass(frozen=True)
class ChokeProperties(ProcessUnitProperties):
    ...

class Choke(ProcessUnit[ChokeProperties]):
    def __init__(
        self,
        process_unit_id: ProcessUnitId,
        fluid_service: FluidService,
        pressure_change: float = 0.0,
    ):
        self._id = process_unit_id
        self._pressure_change = pressure_change
        self._fluid_service = fluid_service

    def get_id(self) -> ProcessUnitId:
        return self._id

    @property
    def pressure_change(self) -> float:
        return self._pressure_change

    def get_properties(self) -> ChokeProperties:
        return ChokeProperties()

    @classmethod
    def from_properties(cls, properties: ChokeProperties) -> "Choke":
        return cls(
            process_unit_id=create_process_unit_id(),
            fluid_service=FluidService(),
        )

    def set_pressure_change(self, pressure_change: float) -> None:
        if pressure_change < 0:
            raise ValueError("Pressure_change cannot be negative")
        self._pressure_change = pressure_change

    def propagate_stream(self, inlet_stream: FluidStream) -> FluidStream:
        if self._pressure_change > 0.0:
            pressure_bara = inlet_stream.pressure_bara - self._pressure_change
            if pressure_bara < 0.0:
                raise OutsideCapacityError("Trying to choke to negative pressure.")
        else:
            # Delta pressure = 0, i.e. don't do anything
            return inlet_stream

        return self._fluid_service.create_stream_from_standard_rate(
            fluid_model=inlet_stream.fluid_model,
            pressure_bara=pressure_bara,
            temperature_kelvin=inlet_stream.temperature_kelvin,
            standard_rate_m3_per_day=inlet_stream.standard_rate_sm3_per_day,
        )
