import logging
from dataclasses import dataclass

from libecalc.domain.process.value_objects.fluid_stream import FluidStream, ProcessConditions

logger = logging.getLogger(__name__)

LIQUID_REMOVAL_THRESHOLD = 0.90


@dataclass(frozen=True)
class LiquidRemover:
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
            molar_mass_in = stream.molar_mass
            vapor_molar_fraction_in = stream.vapor_fraction_molar
            mass_rate_in = stream.mass_rate_kg_per_h
            stream_out = stream.create_stream_with_new_conditions(
                conditions=ProcessConditions(
                    pressure_bara=stream.pressure_bara,
                    temperature_kelvin=stream.temperature_kelvin,
                ),
                remove_liquid=True,
            )
            molar_mass_out = stream_out.molar_mass
            mass_rate_out = mass_rate_in * vapor_molar_fraction_in * molar_mass_out / molar_mass_in
            if mass_rate_out < LIQUID_REMOVAL_THRESHOLD * mass_rate_in:
                logger.warning(
                    "Liquid removal exceeded threshold: more than 10% of inlet mass rate removed.",
                )
            return FluidStream(
                thermo_system=stream_out.thermo_system,
                mass_rate_kg_per_h=mass_rate_out,
            )
        else:
            return stream
