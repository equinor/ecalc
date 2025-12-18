from dataclasses import dataclass
from uuid import UUID

from libecalc.domain.process.entities.process_units.process_unit_type import ProcessUnitType
from libecalc.domain.process.process_system import ProcessUnit
from libecalc.domain.process.value_objects.fluid_stream import FluidStream, ProcessConditions


@dataclass(frozen=True)
class LiquidRemover(ProcessUnit):
    unit_id: UUID

    @staticmethod
    def remove_liquid(stream: FluidStream) -> FluidStream:
        """
        Removes liquid from the fluid stream.

        Args:
            stream (FluidStream): The fluid stream to be scrubbed.

        Returns:
            FluidStream: A new FluidStream with liquid removed.
        """
        if stream.vapor_fraction_molar < 1.0:
            return stream.create_stream_with_new_conditions(
                conditions=ProcessConditions(
                    pressure_bara=stream.pressure_bara,
                    temperature_kelvin=stream.temperature_kelvin,
                ),
                remove_liquid=True,
            )
        else:
            return stream

    def get_id(self) -> UUID:
        return self.unit_id

    def get_type(self) -> str:
        return ProcessUnitType.LIQUID_REMOVER.value
