from __future__ import annotations

from collections import defaultdict

from typing_extensions import Protocol

from libecalc.domain.process.value_objects.fluid_stream.exceptions import (
    EmptyStreamListException,
    IncompatibleEoSModelsException,
    IncompatibleThermoSystemProvidersException,
    ZeroTotalMassRateException,
)
from libecalc.domain.process.value_objects.fluid_stream.fluid_model import FluidComposition, FluidModel
from libecalc.domain.process.value_objects.fluid_stream.fluid_stream import FluidStream
from libecalc.domain.process.value_objects.fluid_stream.process_conditions import ProcessConditions


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

    All streams must have:
    - The same thermo system provider (e.g., all NeqSimThermoSystem)
    - The same EoS model within that provider

    Note: This method is most appropriate when mixing streams with similar temperatures.
    """

    def mix_streams(self, streams: list[FluidStream]) -> FluidStream:
        """Mix multiple streams using component-wise molar balance.

        Args:
            streams: List of streams to mix

        Returns:
            A new Stream instance representing the mixed stream

        Raises:
            EmptyStreamListException: If streams list is empty
            ZeroTotalMassRateException: If total mass rate is zero
            IncompatibleThermoSystemProvidersException: If streams have different thermo system providers
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

        # All streams must have the same thermo system provider
        reference_thermo_provider = type(streams[0].thermo_system).__name__
        for s in streams[1:]:
            current_thermo_provider = type(s.thermo_system).__name__
            if current_thermo_provider != reference_thermo_provider:
                raise IncompatibleThermoSystemProvidersException(reference_thermo_provider, current_thermo_provider)

        # All streams must share the same EoS
        reference_eos_model = streams[0].thermo_system.eos_model
        for s in streams[1:]:
            if s.thermo_system.eos_model != reference_eos_model:
                raise IncompatibleEoSModelsException(reference_eos_model, s.thermo_system.eos_model)

        # Compute total molar flow for each stream
        stream_total_molar_rates = [s.mass_rate_kg_per_h / s.molar_mass for s in streams]
        mix_total_molar_rate = sum(stream_total_molar_rates)

        # Sum molar flow of each component across all streams
        mix_component_molar_rate_dict: defaultdict[str, float] = defaultdict(float)
        for s, total_molar_rate in zip(streams, stream_total_molar_rates):
            normalized_comp = s.thermo_system.composition.normalized()
            for component, mole_fraction in normalized_comp.model_dump().items():
                mix_component_molar_rate_dict[component] += total_molar_rate * mole_fraction

        # Convert to final mole fractions
        mix_composition_dict = {
            comp: (m_rate / mix_total_molar_rate) for comp, m_rate in mix_component_molar_rate_dict.items()
        }
        mix_composition = FluidComposition.model_validate(mix_composition_dict).normalized()

        # Create new conditions
        conditions = ProcessConditions(
            pressure_bara=reference_pressure,
            temperature_kelvin=temperature_mix,
        )

        # Create a new thermo system using the same type as the first stream
        # Note: this assumes the thermo system provider supports initialization with FluidModel and conditions
        first_stream_thermo = streams[0].thermo_system
        mix_fluid_model = FluidModel(
            composition=mix_composition,
            eos_model=reference_eos_model,
        )
        thermo_system_mix = first_stream_thermo.__class__(  # type: ignore[call-arg]
            fluid_model=mix_fluid_model,
            conditions=conditions,
        )

        # Create a new stream with calculated properties
        return FluidStream(
            thermo_system=thermo_system_mix,
            mass_rate_kg_per_h=total_mass_rate,
        )
