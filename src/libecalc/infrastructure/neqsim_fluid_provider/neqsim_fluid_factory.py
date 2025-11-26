from __future__ import annotations

import copy
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

    def __deepcopy__(self, memo: dict) -> NeqSimFluidFactory:
        """Create a deep copy of the factory.

        Since the factory holds references to NeqsimFluid objects via the cached
        _reference_thermo_system property (which can't be pickled due to JVM connections),
        we create a new factory with the same fluid model. The cached properties will be
        lazily recomputed when accessed.
        """
        # Deep copy only the fluid model, create a fresh factory
        new_fluid_model = copy.deepcopy(self._fluid_model, memo)
        return NeqSimFluidFactory(new_fluid_model)

    @property
    def fluid_model(self) -> FluidModel:
        """Get the fluid model used by this factory."""
        return self._fluid_model

    @cached_property
    def _reference_thermo_system(self) -> NeqSimThermoSystem:
        """Create ONE reference thermo system at standard conditions.

        This is the only place where we create a NeqsimFluid via JVM for this factory.
        All subsequent create_thermo_system calls will flash this reference to the
        desired conditions, which is much cheaper than creating a new NeqsimFluid.
        """
        standard_conditions = ProcessConditions.standard_conditions()
        return NeqSimThermoSystem(
            fluid_model=self._fluid_model,
            conditions=standard_conditions,
        )

    @cached_property
    def _standard_density(self) -> float:
        """Get the density at standard conditions for rate conversions."""
        return self._reference_thermo_system.standard_density_gas_phase_after_flash

    def create_thermo_system(self, pressure_bara: float, temperature_kelvin: float) -> ThermoSystemInterface:
        """Create a thermo system at specified conditions.

        Instead of creating a new NeqsimFluid via expensive JVM calls, we flash the
        reference thermo system to the desired conditions. This reuses the existing
        NeqsimFluid and leverages the flash cache for repeated condition combinations.

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
        # Flash the reference system to new conditions (reuses existing NeqsimFluid)
        # Note: remove_liquid=False to match original behavior where systems are
        # created directly at target conditions without liquid removal
        return self._reference_thermo_system.flash_to_conditions(
            conditions=conditions,
            remove_liquid=False,
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
