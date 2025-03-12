from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from libecalc.domain.process.core.stream.conditions import ProcessConditions
from libecalc.domain.process.core.stream.fluid import Fluid, FluidComposition

if TYPE_CHECKING:
    from libecalc.domain.process.core.stream.stream import Stream


class SimplifiedStreamMixing:
    """Implementation of simplified mixing using component-wise molar balance.

    This mixing strategy performs a simplified mixing calculation without requiring
    thermodynamic equilibrium calculations. The approach uses:
    - The mass-weighted average temperature of all streams
    - The lowest pressure among all streams for the resulting mixture
    - Component-wise molar balance for composition calculation
    - No thermodynamic equilibrium calculations

    Note: This method is most appropriate when mixing streams with similar temperatures.
    """

    def mix_streams(self, streams: list[Stream]) -> Stream:
        """Mix multiple streams using component-wise molar balance.

        Args:
            streams: List of streams to mix

        Returns:
            A new Stream instance representing the mixed stream

        Raises:
            ValueError: If streams list is empty or if total mass rate is zero
            ValueError: If streams have different EoS models
        """
        if not streams:
            raise ValueError("Cannot mix empty list of streams")

        total_mass_rate = sum(stream.mass_rate for stream in streams)
        if total_mass_rate == 0:
            raise ValueError("Total mass rate cannot be zero")

        # Calculate mass-weighted average temperature
        reference_temperature = (
            sum(stream.mass_rate * stream.conditions.temperature for stream in streams) / total_mass_rate
        )

        reference_pressure = min(stream.conditions.pressure for stream in streams)

        # Use the EoS model from the first stream (all streams must have the same EoS model, enforced below)
        reference_eos_model = streams[0].fluid.eos_model

        for stream in streams[1:]:
            if stream.fluid.eos_model != reference_eos_model:
                raise ValueError(
                    f"Cannot mix streams with different EoS models: "
                    f"{reference_eos_model} vs {stream.fluid.eos_model}"
                )

        stream_total_molar_rates_list = []
        for stream in streams:
            stream_total_molar_rate = stream.mass_rate / stream.fluid.molar_mass
            stream_total_molar_rates_list.append(stream_total_molar_rate)

        mix_total_molar_rate = sum(stream_total_molar_rates_list)

        mix_component_molar_rate_dict: defaultdict[str, float] = defaultdict(float)

        # Sum molar flow of each component across all streams
        for stream, stream_total_molar_rate in zip(streams, stream_total_molar_rates_list):
            normalized_stream_composition = stream.fluid.composition.normalized()
            for component, stream_component_mole_fraction in normalized_stream_composition.model_dump().items():
                stream_component_molar_rate = stream_total_molar_rate * stream_component_mole_fraction
                mix_component_molar_rate_dict[component] += stream_component_molar_rate

        # Convert to final mole fractions
        mix_composition_dict = {
            component: mix_comp_molar_rate / mix_total_molar_rate
            for component, mix_comp_molar_rate in mix_component_molar_rate_dict.items()
        }

        mix_composition = FluidComposition.model_validate(mix_composition_dict).normalized()

        result_fluid = Fluid(composition=mix_composition, eos_model=reference_eos_model)

        # Import here to avoid circular import
        from libecalc.domain.process.core.stream.stream import Stream

        return Stream(
            fluid=result_fluid,
            conditions=ProcessConditions(temperature=reference_temperature, pressure=reference_pressure),
            mass_rate=total_mass_rate,
        )
