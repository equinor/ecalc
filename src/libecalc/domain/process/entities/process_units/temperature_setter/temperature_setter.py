from uuid import UUID

from libecalc.domain.process.entities.process_units.process_unit_type import ProcessUnitType
from libecalc.domain.process.process_system import ProcessUnit
from libecalc.domain.process.value_objects.fluid_stream import FluidStream, ProcessConditions


class TemperatureSetter(ProcessUnit):
    def __init__(self, required_temperature_kelvin: float, unit_id: UUID):
        self._required_temperature_kelvin = required_temperature_kelvin
        self._unit_id = unit_id

    @property
    def required_temperature_kelvin(self) -> float:
        return self._required_temperature_kelvin

    def set_temperature(self, stream: FluidStream) -> FluidStream:
        if stream.temperature_kelvin > self.required_temperature_kelvin:
            return stream.create_stream_with_new_conditions(
                conditions=ProcessConditions(
                    pressure_bara=stream.pressure_bara,
                    temperature_kelvin=self.required_temperature_kelvin,
                )
            )
        return stream

    def get_id(self) -> UUID:
        return self._unit_id

    def get_type(self) -> str:
        return ProcessUnitType.TEMPERATURE_SETTER.value
