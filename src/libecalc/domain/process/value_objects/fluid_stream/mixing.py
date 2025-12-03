from __future__ import annotations

from collections import defaultdict

from typing_extensions import Protocol

from libecalc.domain.process.value_objects.fluid_stream.exceptions import (
    EmptyStreamListException,
    IncompatibleEoSModelsException,
    ZeroTotalMassRateException,
)
from libecalc.domain.process.value_objects.fluid_stream.fluid_model import FluidComposition, FluidModel
from libecalc.domain.process.value_objects.fluid_stream.fluid_stream import FluidStream


class StreamMixingStrategy(Protocol):
    """Protocol for stream mixing strategies"""

    def mix_streams(self, streams: list[FluidStream]) -> FluidStream:
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

    All streams must have the same EoS model.

    Note: This method is most appropriate when mixing streams with similar temperatures.
    """

    def mix_streams(self, streams: list[FluidStream]) -> FluidStream:
        """Mix multiple streams using component-wise molar balance.

        Args:
            streams: List of streams to mix

        Returns:
            A new FluidStream instance representing the mixed stream

        Raises:
            EmptyStreamListException: If streams list is empty
            ZeroTotalMassRateException: If total mass rate is zero
            IncompatibleEoSModelsException: If streams have different EoS models
        """
        if not streams:
            raise EmptyStreamListException()

        total_mass_rate = sum(s.mass_rate_kg_per_h for s in streams)
        if total_mass_rate == 0:
            raise ZeroTotalMassRateException()

        # Calculate mass-weighted average temperature
        temperature_mix = sum(s.mass_rate_kg_per_h * s.temperature_kelvin for s in streams) / total_mass_rate

        # Lowest pressure among all streams
        reference_pressure = min(s.pressure_bara for s in streams)

        # All streams must share the same EoS model
        reference_eos_model = streams[0].fluid_model.eos_model
        for s in streams[1:]:
            if s.fluid_model.eos_model != reference_eos_model:
                raise IncompatibleEoSModelsException(reference_eos_model, s.fluid_model.eos_model)

        # Compute total molar flow for each stream
        stream_total_molar_rates = [s.mass_rate_kg_per_h / s.molar_mass for s in streams]
        mix_total_molar_rate = sum(stream_total_molar_rates)

        # Sum molar flow of each component across all streams
        mix_component_molar_rate_dict: defaultdict[str, float] = defaultdict(float)
        for s, total_molar_rate in zip(streams, stream_total_molar_rates):
            normalized_comp = s.fluid_model.composition.normalized()
            for component, mole_fraction in normalized_comp.model_dump().items():
                mix_component_molar_rate_dict[component] += total_molar_rate * mole_fraction

        # Convert to final mole fractions
        mix_composition_dict = {
            comp: (m_rate / mix_total_molar_rate) for comp, m_rate in mix_component_molar_rate_dict.items()
        }
        mix_composition = FluidComposition.model_validate(mix_composition_dict).normalized()

        # Create the mixed fluid model
        mix_fluid_model = FluidModel(
            composition=mix_composition,
            eos_model=reference_eos_model,
        )

        # Use NeqSimFluidService to get properties at mixed conditions
        from ecalc_neqsim_wrapper.fluid_service import NeqSimFluidService

        mix_props = NeqSimFluidService.instance().get_properties(
            fluid_model=mix_fluid_model,
            pressure_bara=reference_pressure,
            temperature_kelvin=temperature_mix,
            remove_liquid=False,
        )

        # Create a new stream with calculated properties
        return FluidStream(
            fluid_model=mix_fluid_model,
            fluid_properties=mix_props,
            mass_rate_kg_per_h=total_mass_rate,
        )
