from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from functools import cached_property
from typing import ClassVar, Optional, Protocol

from libecalc.common.string.string_utils import generate_id
from libecalc.common.units import UnitConstants
from libecalc.domain.process.core.stream.conditions import ProcessConditions
from libecalc.domain.process.core.stream.fluid import Fluid, FluidComposition


class MixingStrategy(Protocol):
    """Protocol for stream mixing strategies"""

    def mix_streams(self, streams: list[Stream]) -> Stream:
        """Mix multiple streams into a single resultant stream"""
        ...


class SimplifiedComponentMixing:
    """Implementation of simplified mixing using component-wise molar balance

    This mixing approach does not require thermodynamic equilibrium calculations.
    - It uses the first stream's temperature, which is a simplification.
      (Note: This means that the inlet streams should be similar in temperature for it to make sense)
    - It uses the lowest pressure among all streams for the resulting mixture,
      which is standard practice.
    """

    def mix_streams(self, streams: list[Stream]) -> Stream:
        """Mix multiple streams using a component-wise molar balance approach

        Simplifications:
        - The temperature of the first stream is used for the resulting mixture
        - The lowest pressure among all streams is used for the resulting mixture
        - No rigorous energy balance or flash calculations are performed
        """
        if not streams:
            raise ValueError("Cannot mix empty list of streams")

        total_mass_rate = sum(stream.mass_rate for stream in streams)
        if total_mass_rate == 0:
            raise ValueError("Total mass rate cannot be zero")

        reference_temperature = streams[0].conditions.temperature

        reference_pressure = min(stream.conditions.pressure for stream in streams)

        # For simplicity, use the EoS model from the first stream
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
            for component, stream_component_mole_fraction in stream.fluid.composition.model_dump().items():
                stream_component_molar_rate = stream_total_molar_rate * stream_component_mole_fraction
                mix_component_molar_rate_dict[component] += stream_component_molar_rate

        # Calculate the total moles to ensure proper normalization
        # total_molar_rate = sum(component_molar_rate_total.values())

        # Convert to final mole fractions - normalize to ensure they sum to 1.0
        mix_composition_dict = {
            component: mix_comp_molar_rate / mix_total_molar_rate
            for component, mix_comp_molar_rate in mix_component_molar_rate_dict.items()
        }

        mix_composition = FluidComposition.model_validate(mix_composition_dict)

        result_fluid = Fluid(composition=mix_composition, eos_model=reference_eos_model)

        name = "-".join(stream.name for stream in streams if stream.name)
        name = name if name else f"Mixed Stream {generate_id()}"

        return Stream(
            name=name,
            fluid=result_fluid,
            conditions=ProcessConditions(temperature=reference_temperature, pressure=reference_pressure),
            mass_rate=total_mass_rate,
        )


@dataclass(frozen=True)
class Stream:
    """
    Represents a fluid stream with its properties and conditions.

    This class consolidates the functionality from various existing stream
    implementations in the system.

    Attributes:
        fluid: Fluid object containing composition and EoS model
        conditions: Process conditions (temperature and pressure)
        mass_rate: Mass flow rate [kg/h]
        name: Optional identifier for the stream
    """

    fluid: Fluid
    conditions: ProcessConditions
    mass_rate: float
    name: Optional[str] = None

    # Default mixing strategy (class variable)
    _mixing_strategy: ClassVar[MixingStrategy] = SimplifiedComponentMixing()

    def __post_init__(self):
        """Validate stream properties"""
        if self.mass_rate < 0:
            raise ValueError(f"Mass rate must be non-negative, got {self.mass_rate}")

    @property
    def temperature(self) -> float:
        """Get stream temperature [K]."""
        return self.conditions.temperature

    @property
    def pressure(self) -> float:
        """Get stream pressure [bara]."""
        return self.conditions.pressure

    @cached_property
    def density(self) -> float:
        """Get density [kg/m³]."""
        return self._get_thermodynamic_engine().get_density(self.fluid, self.pressure, self.temperature)

    @cached_property
    def molar_mass(self) -> float:
        """Get molar mass of the fluid [kg/kmol]."""
        return self._get_thermodynamic_engine().get_molar_mass(self.fluid)

    @cached_property
    def standard_density_gas_phase_after_flash(self) -> float:
        """Get gas phase density at standard conditions after TP flash and liquid removal [kg/m³]."""
        return self._get_thermodynamic_engine().get_standard_density_gas_phase_after_flash(self.fluid)

    @cached_property
    def enthalpy(self) -> float:
        """Get specific enthalpy [J/kg]."""
        return self._get_thermodynamic_engine().get_enthalpy(self.fluid, self.pressure, self.temperature)

    @cached_property
    def z(self) -> float:
        """Get compressibility factor [-]."""
        return self._get_thermodynamic_engine().get_z(self.fluid, self.pressure, self.temperature)

    @cached_property
    def kappa(self) -> float:
        """Get isentropic exponent [-]."""
        return self._get_thermodynamic_engine().get_kappa(self.fluid, self.pressure, self.temperature)

    @cached_property
    def phase_fractions(self) -> dict[str, float]:
        """Get current phase distribution [-]."""
        return self._get_thermodynamic_engine().get_phase_fractions(self.fluid, self.pressure, self.temperature)

    @cached_property
    def volumetric_rate(self) -> float:
        """Calculate volumetric flow rate [m³/s]."""
        return self.mass_rate / self.density

    @cached_property
    def standard_rate(self) -> float:
        """Calculate standard volumetric flow rate [Sm³/day]."""
        return self.mass_rate / self.standard_density_gas_phase_after_flash * UnitConstants.HOURS_PER_DAY

    def create_stream_with_new_conditions(self, new_conditions: ProcessConditions) -> Stream:
        """Create a new stream with modified conditions.

        Args:
            new_conditions: New process conditions to apply

        Returns:
            A new Stream instance with the modified conditions
        """
        return Stream(
            fluid=self.fluid,
            conditions=new_conditions,
            mass_rate=self.mass_rate,
            name=f"{self.name}_modified" if self.name else None,
        )

    def create_stream_with_new_pressure_and_temperature(self, new_pressure: float, new_temperature: float) -> Stream:
        """Create a new stream with modified pressure and temperature.

        Args:
            new_pressure: New pressure [bara]
            new_temperature: New temperature [K]

        Returns:
            A new Stream instance with the modified pressure and temperature
        """
        return self.create_stream_with_new_conditions(
            ProcessConditions(pressure=new_pressure, temperature=new_temperature)
        )

    def create_stream_with_new_pressure_and_enthalpy_change(
        self, new_pressure: float, enthalpy_change: float
    ) -> Stream:
        """Create a new stream with modified pressure and changed enthalpy.
        TODO: This is a temporary method with only the

        This simulates a PH-flash operation.

        Args:
            new_pressure: Target pressure [bara]
            enthalpy_change: Change in specific enthalpy [J/kg]

        Returns:
            A new Stream instance with the modified pressure and resulting temperature
        """
        from ecalc_neqsim_wrapper.thermo import NeqsimFluid

        neqsim_fluid = NeqsimFluid.create_thermo_system(
            composition=self.fluid.composition,
            temperature_kelvin=self.temperature,
            pressure_bara=self.pressure,
            eos_model=self.fluid.eos_model,
        )

        # Use NeqSim's PH flash to get the new state
        neqsim_fluid = neqsim_fluid.set_new_pressure_and_enthalpy(
            new_pressure=new_pressure,
            new_enthalpy_joule_per_kg=neqsim_fluid.enthalpy_joule_per_kg + enthalpy_change,
            remove_liquid=True,
        )

        # Return a new stream with the calculated temperature
        return self.create_stream_with_new_pressure_and_temperature(
            new_pressure=new_pressure, new_temperature=neqsim_fluid.temperature_kelvin
        )

    @classmethod
    def mix(cls, streams: list[Stream]) -> Stream:
        """Mix multiple streams into one.

        Args:
            streams: List of streams to mix, must have same temperature and pressure

        Returns:
            A new Stream instance representing the mixed stream
        """
        return cls._mixing_strategy.mix_streams(streams)

    def _get_thermodynamic_engine(self):
        """Get the thermodynamic engine from the fluid."""
        return self.fluid._get_thermodynamic_engine()

    @classmethod
    def from_standard_rate(
        cls,
        fluid: Fluid,
        conditions: ProcessConditions,
        standard_rate: float,  # Sm³/day
        name: Optional[str] = None,
    ) -> Stream:
        """Create a stream from standard volumetric flow rate instead of mass rate.

        Args:
            fluid: Fluid object containing composition and EoS model
            conditions: Process conditions (temperature and pressure)
            standard_rate: Volumetric flow rate at standard conditions [Sm³/day]
            name: Optional identifier for the stream

        Returns:
            A new Stream instance with mass rate calculated from standard rate
        """
        # Create a temporary fluid to get standard density
        standard_density = fluid._get_thermodynamic_engine().get_standard_density_gas_phase_after_flash(fluid)

        # Convert standard rate to mass rate
        mass_rate = standard_rate * standard_density / UnitConstants.HOURS_PER_DAY

        return cls(fluid=fluid, conditions=conditions, mass_rate=mass_rate, name=name)
