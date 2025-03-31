from __future__ import annotations

from collections import defaultdict

from typing_extensions import Protocol

from libecalc.common.fluid import FluidComposition
from libecalc.domain.process.core.stream.conditions import ProcessConditions
from libecalc.domain.process.core.stream.exceptions import (
    EmptyStreamListException,
    IncompatibleEoSModelsException,
    ZeroTotalMassRateException,
)
from libecalc.domain.process.core.stream.stream import Stream
from libecalc.domain.process.core.stream.thermo_system import NeqSimThermoSystem


class StreamMixingStrategy(Protocol):
    """Protocol for stream mixing strategies"""

    def mix_streams(self, streams: list[Stream]) -> Stream:
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

    def mix_streams(self, streams: list[Stream]) -> Stream:
        """Mix multiple streams using component-wise molar balance.

        Args:
            streams: List of streams to mix

        Returns:
            A new Stream instance representing the mixed stream

        Raises:
            EmptyStreamListException: If streams list is empty
            ZeroTotalMassRateException: If total mass rate is zero
            IncompatibleEoSModelsException: If streams have different EoS models
        """
        if not streams:
            raise EmptyStreamListException()

        total_mass_rate = sum(s.mass_rate for s in streams)
        if total_mass_rate == 0:
            raise ZeroTotalMassRateException()

        # Calculate mass-weighted average temperature
        reference_temperature = sum(s.mass_rate * s.temperature_kelvin for s in streams) / total_mass_rate

        # Lowest pressure among all streams
        reference_pressure = min(s.pressure_bara for s in streams)

        # All streams must share the same EoS
        reference_eos_model = streams[0].thermo_system.eos_model
        for s in streams[1:]:
            if s.thermo_system.eos_model != reference_eos_model:
                raise IncompatibleEoSModelsException(reference_eos_model, s.thermo_system.eos_model)

        # Compute total molar flow for each stream
        stream_total_molar_rates = [s.mass_rate / s.molar_mass for s in streams]
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
            temperature_kelvin=reference_temperature,
        )

        # Create a new thermo system
        mix_thermo_system = NeqSimThermoSystem(
            composition=mix_composition,
            eos_model=reference_eos_model,
            conditions=conditions,
        )

        # Create a new stream with calculated properties
        return Stream(
            thermo_system=mix_thermo_system,
            mass_rate=total_mass_rate,
        )
