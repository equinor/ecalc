from __future__ import annotations

from collections import defaultdict

from typing_extensions import Protocol

from libecalc.domain.process.core.stream.conditions import ProcessConditions
from libecalc.domain.process.core.stream.fluid import Fluid, FluidComposition, ThermodynamicEngine
from libecalc.domain.process.core.stream.stream import Stream


class StreamMixingStrategy(Protocol):
    """Protocol for stream mixing strategies"""

    def mix_streams(self, streams: list[Stream], engine: ThermodynamicEngine | None = None) -> Stream:
        """Mix multiple streams into a single resultant stream"""
        ...


class SimplifiedStreamMixing(StreamMixingStrategy):
    """Implementation of simplified mixing using component-wise molar balance.

    This mixing strategy performs a simplified mixing calculation without requiring
    thermodynamic equilibrium calculations. The approach uses:
    - The mass-weighted average temperature of all streams
    - The lowest pressure among all streams for the resulting mixture
    - Component-wise molar balance for composition calculation
    - No thermodynamic equilibrium calculations

    Note: This method is most appropriate when mixing streams with similar temperatures.
    """

    def mix_streams(self, streams: list[Stream], engine: ThermodynamicEngine | None = None) -> Stream:
        """Mix multiple streams using component-wise molar balance.

        Args:
            streams: List of streams to mix
            engine: (Optional) ThermodynamicEngine instance to use for the mixed fluid.
                If None, the new Fluid reuses the engine from the first stream.

        Returns:
            A new Stream instance representing the mixed stream

        Raises:
            ValueError: If streams list is empty or if total mass rate is zero
            ValueError: If streams have different EoS models
        """
        if not streams:
            raise ValueError("Cannot mix empty list of streams")

        total_mass_rate = sum(s.mass_rate for s in streams)
        if total_mass_rate == 0:
            raise ValueError("Total mass rate cannot be zero")

        # Calculate mass-weighted average temperature
        reference_temperature = sum(s.mass_rate * s.conditions.temperature_kelvin for s in streams) / total_mass_rate

        # Lowest pressure among all streams
        reference_pressure = min(s.conditions.pressure_bara for s in streams)

        # All streams must share the same EoS
        reference_eos_model = streams[0].fluid.eos_model
        for s in streams[1:]:
            if s.fluid.eos_model != reference_eos_model:
                raise ValueError(
                    f"Cannot mix streams with different EoS models: " f"{reference_eos_model} vs {s.fluid.eos_model}"
                )

        # Choose the thermodynamic engine for the resulting fluid
        # If none is given, use the first stream's engine
        if engine is None:
            engine = streams[0].fluid._thermodynamic_engine

        # Compute total molar flow for each stream
        stream_total_molar_rates = [s.mass_rate / s.fluid.molar_mass for s in streams]
        mix_total_molar_rate = sum(stream_total_molar_rates)

        # Sum molar flow of each component across all streams
        mix_component_molar_rate_dict: defaultdict[str, float] = defaultdict(float)
        for s, total_molar_rate in zip(streams, stream_total_molar_rates):
            normalized_comp = s.fluid.composition.normalized()
            for component, mole_fraction in normalized_comp.model_dump().items():
                mix_component_molar_rate_dict[component] += total_molar_rate * mole_fraction

        # Convert to final mole fractions
        mix_composition_dict = {
            comp: (m_rate / mix_total_molar_rate) for comp, m_rate in mix_component_molar_rate_dict.items()
        }
        mix_composition = FluidComposition.model_validate(mix_composition_dict).normalized()

        # Create a Fluid reusing the chosen EOS model and engine
        result_fluid = Fluid(composition=mix_composition, eos_model=reference_eos_model, _thermodynamic_engine=engine)

        # Import here to avoid circular import
        from libecalc.domain.process.core.stream.stream import Stream

        return Stream(
            fluid=result_fluid,
            conditions=ProcessConditions(temperature_kelvin=reference_temperature, pressure_bara=reference_pressure),
            mass_rate=total_mass_rate,
        )
