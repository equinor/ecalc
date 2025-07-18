from __future__ import annotations

from functools import cached_property

import numpy as np
from numpy.typing import NDArray

from libecalc.common.units import UnitConstants
from libecalc.domain.process.value_objects.fluid_stream import FluidStream, ProcessConditions
from libecalc.domain.process.value_objects.fluid_stream.fluid_factory import FluidFactoryInterface
from libecalc.domain.process.value_objects.fluid_stream.fluid_model import FluidModel
from libecalc.domain.process.value_objects.fluid_stream.thermo_system import ThermoSystemInterface
from libecalc.infrastructure.neqsim_fluid_provider.neqsim_thermo_system import NeqSimThermoSystem


class NeqSimFluidFactory(FluidFactoryInterface):
    """Concrete implementation of FluidFactoryInterface using NeqSim."""

    def __init__(self, fluid_model: FluidModel):
        self._fluid_model = fluid_model

    @property
    def fluid_model(self) -> FluidModel:
        """Get the fluid model used by this factory."""
        return self._fluid_model

    @cached_property
    def _standard_density(self) -> float:
        """Get the density at standard conditions for rate conversions."""
        standard_conditions = ProcessConditions.standard_conditions()
        thermo_system = self.create_thermo_system(
            pressure_bara=standard_conditions.pressure_bara,
            temperature_kelvin=standard_conditions.temperature_kelvin,
        )
        return thermo_system.standard_density_gas_phase_after_flash

    def create_thermo_system(self, pressure_bara: float, temperature_kelvin: float) -> ThermoSystemInterface:
        """Create a thermo system at specified conditions.

        Args:
            pressure_bara: Pressure in bara
            temperature_kelvin: Temperature in Kelvin

        Returns:
            A NeqSimThermoSystem instance at the specified conditions
        """
        conditions = ProcessConditions(
            pressure_bara=pressure_bara,
            temperature_kelvin=temperature_kelvin,
        )
        return NeqSimThermoSystem(
            fluid_model=self._fluid_model,
            conditions=conditions,
        )

    def create_stream_from_standard_rate(
        self, pressure_bara: float, temperature_kelvin: float, standard_rate_m3_per_day: float
    ) -> FluidStream:
        """Create a fluid stream from standard volumetric rate.

        Args:
            pressure_bara: Pressure in bara
            temperature_kelvin: Temperature in Kelvin
            standard_rate: Volumetric flow rate at standard conditions [Sm³/day]

        Returns:
            A FluidStream instance
        """
        thermo_system = self.create_thermo_system(
            pressure_bara=pressure_bara,
            temperature_kelvin=temperature_kelvin,
        )
        return FluidStream.from_standard_rate(
            standard_rate_m3_per_day=standard_rate_m3_per_day,
            thermo_system=thermo_system,
        )

    def create_stream_from_mass_rate(
        self, pressure_bara: float, temperature_kelvin: float, mass_rate_kg_per_h: float
    ) -> FluidStream:
        """Create a fluid stream from mass rate.

        Args:
            pressure_bara: Pressure in bara
            temperature_kelvin: Temperature in Kelvin
            mass_rate: Mass flow rate [kg/h]

        Returns:
            A FluidStream instance
        """
        thermo_system = self.create_thermo_system(
            pressure_bara=pressure_bara,
            temperature_kelvin=temperature_kelvin,
        )
        return FluidStream(
            thermo_system=thermo_system,
            mass_rate_kg_per_h=mass_rate_kg_per_h,
        )

    def standard_rate_to_mass_rate(
        self, standard_rate_m3_per_day: float | NDArray[np.float64]
    ) -> float | NDArray[np.float64]:
        """Convert standard volumetric rate to mass rate.

        Args:
            standard_rate: Volumetric flow rate at standard conditions [Sm³/day]

        Returns:
            Mass flow rate [kg/h]
        """
        mass_rate_kg_per_hour = standard_rate_m3_per_day * self._standard_density / UnitConstants.HOURS_PER_DAY
        if isinstance(mass_rate_kg_per_hour, np.ndarray):
            return np.array(mass_rate_kg_per_hour)
        else:
            return float(mass_rate_kg_per_hour)

    def mass_rate_to_standard_rate(
        self, mass_rate_kg_per_h: float | NDArray[np.float64]
    ) -> float | NDArray[np.float64]:
        """Convert mass rate to standard volumetric rate.

        Args:
            mass_rate: Mass flow rate [kg/h]

        Returns:
            Volumetric flow rate at standard conditions [Sm³/day]
        """
        standard_rate = mass_rate_kg_per_h / self._standard_density * UnitConstants.HOURS_PER_DAY
        if isinstance(standard_rate, np.ndarray):
            return np.array(standard_rate)
        else:
            return float(standard_rate)

    def create_fluid_factory_from_fluid_model(self, fluid_model: FluidModel) -> FluidFactoryInterface:
        """Create a new fluid factory from a fluid model.

        Args:
            fluid_model: The fluid model to use for the new factory

        Returns:
            A new NeqSimFluidFactory instance with the given fluid model
        """
        return NeqSimFluidFactory(fluid_model)
