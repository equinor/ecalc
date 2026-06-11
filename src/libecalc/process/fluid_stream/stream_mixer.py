import dataclasses
from collections import defaultdict

from libecalc.process.fluid_stream.exceptions import (
    EmptyStreamListException,
    IncompatibleEoSModelsException,
    ZeroTotalMassRateException,
)
from libecalc.process.fluid_stream.fluid import Fluid
from libecalc.process.fluid_stream.fluid_model import FluidComposition, FluidModel
from libecalc.process.fluid_stream.fluid_service import FluidService
from libecalc.process.fluid_stream.fluid_stream import FluidStream


class StreamMixer:
    """Process unit for mixing multiple fluid streams.

    Mixing is adiabatic (isenthalpic): with no shaft work and negligible kinetic
    and potential energy, total enthalpy is conserved across the mixing tee. The
    outlet specific enthalpy is the mass-weighted average of the inlet specific
    enthalpies, and a PH flash at the outlet pressure yields the correct outlet
    temperature and phase state.

    - Composition: component-wise molar balance across all streams.
    - Pressure: the lowest inlet pressure - the only pressure a passive mixing tee
      can reach without adding work (higher pressure feeds throttle down to it).
    - Temperature: solved by PH flash to conserve enthalpy.

    All inlet streams must share the same EoS model. Mixing streams modelled with
    different equations of state is not physically meaningful, since their
    properties (enthalpy, density, phase behaviour) are computed by different
    models and are not mutually consistent.
    """

    def __init__(self, fluid_service: FluidService):
        self._fluid_service = fluid_service

    def mix_streams(self, streams: list[FluidStream]) -> FluidStream:
        """Mix multiple streams using isenthalpic mixing and a molar composition balance.

        Args:
            streams: List of streams to mix (must have same EoS model)

        Returns:
            A new FluidStream representing the mixed stream

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

        # All streams must share the same EoS model so their enthalpies are on a
        # consistent reference state and may be summed.
        reference_eos_model = streams[0].fluid_model.eos_model
        for s in streams[1:]:
            if s.fluid_model.eos_model != reference_eos_model:
                raise IncompatibleEoSModelsException(reference_eos_model, s.fluid_model.eos_model)

        # Outlet pressure is the lowest inlet pressure
        outlet_pressure = min(s.pressure_bara for s in streams)

        # Mass-weighted average temperature - used only as the PH-flash initial guess
        temperature_guess = sum(s.mass_rate_kg_per_h * s.temperature_kelvin for s in streams) / total_mass_rate

        # Isenthalpic mixing: outlet specific enthalpy is the mass-weighted average
        # of the inlet specific enthalpies (total enthalpy conserved).
        outlet_enthalpy_joule_per_kg = (
            sum(s.mass_rate_kg_per_h * s.enthalpy_joule_per_kg for s in streams) / total_mass_rate
        )

        # Compute total molar flow for each stream
        stream_total_molar_rates = [s.mass_rate_kg_per_h / s.molar_mass for s in streams]
        mix_total_molar_rate = sum(stream_total_molar_rates)

        # Sum molar flow of each component across all streams
        mix_component_molar_rate_dict: defaultdict[str, float] = defaultdict(float)
        for s, total_molar_rate in zip(streams, stream_total_molar_rates):
            normalized_comp = s.fluid_model.composition.normalized()
            for component, mole_fraction in dataclasses.asdict(normalized_comp).items():
                mix_component_molar_rate_dict[component] += total_molar_rate * mole_fraction

        # Convert to final mole fractions
        mix_composition_dict = {
            comp: (m_rate / mix_total_molar_rate) for comp, m_rate in mix_component_molar_rate_dict.items()
        }
        mix_composition = FluidComposition(**mix_composition_dict).normalized()

        # Create the mixed fluid model
        mix_fluid_model = FluidModel(
            composition=mix_composition,
            eos_model=reference_eos_model,
        )

        # Solve outlet temperature by conserving enthalpy (PH flash)
        mix_props = self._fluid_service.flash_ph(
            fluid_model=mix_fluid_model,
            pressure_bara=outlet_pressure,
            target_enthalpy_joule_per_kg=outlet_enthalpy_joule_per_kg,
            temperature_guess_kelvin=temperature_guess,
        )

        # Create a new stream with calculated properties
        mix_fluid = Fluid(fluid_model=mix_fluid_model, properties=mix_props)
        return FluidStream(fluid=mix_fluid, mass_rate_kg_per_h=total_mass_rate)
