"""NeqSim implementation of the Fluid protocol.

This module provides NeqSimFluidFactory, which implements the Fluid protocol
using NeqSim for thermodynamic calculations via NeqSimFluidService.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray

from libecalc.common.units import UnitConstants
from libecalc.domain.process.value_objects.fluid_stream.fluid_model import FluidModel
from libecalc.domain.process.value_objects.fluid_stream.fluid_properties import FluidProperties


@dataclass(frozen=True)
class NeqSimFluidFactory:
    """NeqSim implementation of the Fluid protocol.

    This is a frozen dataclass that holds fluid_model + fluid_properties,
    representing a fluid at a specific thermodynamic state.
    Flash operations use NeqSimFluidService internally and return new instances.

    The factory supports lazy initialization - if created with from_fluid_model(),
    fluid properties are computed on first access rather than immediately.

    Example usage:
        # Create fluid at conditions
        fluid = NeqSimFluidFactory.create(fluid_model, pressure_bara=40, temperature_kelvin=300)

        # Flash to new conditions
        new_fluid = fluid.flash_pt(new_pressure, new_temperature)

        # Create stream
        stream = fluid.to_stream(mass_rate_kg_per_h=1000)
    """

    fluid_model: FluidModel
    _fluid_properties: FluidProperties | None = field(default=None, repr=False)

    @property
    def fluid_properties(self) -> FluidProperties:
        """Get fluid properties, computing lazily if needed."""
        if self._fluid_properties is None:
            # Lazy initialization - compute properties at standard conditions
            from ecalc_neqsim_wrapper.fluid_service import NeqSimFluidService

            props = NeqSimFluidService.instance().get_properties(
                fluid_model=self.fluid_model,
                pressure_bara=UnitConstants.STANDARD_PRESSURE_BARA,
                temperature_kelvin=UnitConstants.STANDARD_TEMPERATURE_KELVIN,
                remove_liquid=False,
            )
            # Use object.__setattr__ to bypass frozen dataclass restriction
            object.__setattr__(self, "_fluid_properties", props)
        return self._fluid_properties  # type: ignore[return-value]

    @classmethod
    def create(
        cls,
        fluid_model: FluidModel,
        pressure_bara: float,
        temperature_kelvin: float,
        remove_liquid: bool = False,
    ) -> NeqSimFluidFactory:
        """Factory method to create fluid at specified conditions.

        Args:
            fluid_model: The fluid model (composition + EoS)
            pressure_bara: Pressure in bara
            temperature_kelvin: Temperature in Kelvin
            remove_liquid: Whether to remove liquid phase

        Returns:
            A new NeqSimFluidFactory at the specified conditions
        """
        from ecalc_neqsim_wrapper.fluid_service import NeqSimFluidService

        props = NeqSimFluidService.instance().get_properties(
            fluid_model=fluid_model,
            pressure_bara=pressure_bara,
            temperature_kelvin=temperature_kelvin,
            remove_liquid=remove_liquid,
        )
        return cls(fluid_model=fluid_model, _fluid_properties=props)

    def flash_pt(
        self,
        pressure_bara: float,
        temperature_kelvin: float,
        remove_liquid: bool = False,
    ) -> NeqSimFluidFactory:
        """TP flash - returns new Fluid at given conditions.

        Args:
            pressure_bara: Target pressure in bara
            temperature_kelvin: Target temperature in Kelvin
            remove_liquid: Whether to remove liquid phase after flash

        Returns:
            New NeqSimFluidFactory instance at the target conditions
        """
        from ecalc_neqsim_wrapper.fluid_service import NeqSimFluidService

        new_props = NeqSimFluidService.instance().get_properties(
            fluid_model=self.fluid_model,
            pressure_bara=pressure_bara,
            temperature_kelvin=temperature_kelvin,
            remove_liquid=remove_liquid,
        )
        return NeqSimFluidFactory(fluid_model=self.fluid_model, _fluid_properties=new_props)

    def flash_ph(
        self,
        pressure_bara: float,
        enthalpy_change_joule_per_kg: float,
        remove_liquid: bool = False,
    ) -> NeqSimFluidFactory:
        """PH flash - returns new Fluid with enthalpy change applied.

        Args:
            pressure_bara: Target pressure in bara
            enthalpy_change_joule_per_kg: Change in specific enthalpy [J/kg]
            remove_liquid: Whether to remove liquid phase after flash

        Returns:
            New NeqSimFluidFactory instance at the resulting conditions
        """
        from ecalc_neqsim_wrapper.fluid_service import NeqSimFluidService

        target_enthalpy = self.fluid_properties.enthalpy_joule_per_kg + enthalpy_change_joule_per_kg
        new_props = NeqSimFluidService.instance().flash_ph(
            fluid_model=self.fluid_model,
            pressure_bara=pressure_bara,
            target_enthalpy=target_enthalpy,
            remove_liquid=remove_liquid,
        )
        return NeqSimFluidFactory(fluid_model=self.fluid_model, _fluid_properties=new_props)

    def to_stream(
        self,
        *,
        mass_rate_kg_per_h: float | None = None,
        standard_rate_m3_per_day: float | None = None,
    ):
        """Create a FluidStream from this fluid with specified rate.

        Args:
            mass_rate_kg_per_h: Mass flow rate [kg/h]
            standard_rate_m3_per_day: Volumetric flow rate at standard conditions [Sm3/day]

        Returns:
            FluidStream with this fluid's properties and specified rate

        Raises:
            ValueError: If neither rate is specified
        """
        from libecalc.domain.process.value_objects.fluid_stream import FluidStream

        if mass_rate_kg_per_h is not None:
            return FluidStream(
                fluid_model=self.fluid_model,
                fluid_properties=self.fluid_properties,
                mass_rate_kg_per_h=mass_rate_kg_per_h,
            )
        elif standard_rate_m3_per_day is not None:
            mass_rate = self.standard_rate_to_mass_rate(standard_rate_m3_per_day)
            return FluidStream(
                fluid_model=self.fluid_model,
                fluid_properties=self.fluid_properties,
                mass_rate_kg_per_h=float(mass_rate),  # type: ignore[arg-type]
            )
        raise ValueError("Must specify either mass_rate_kg_per_h or standard_rate_m3_per_day")

    def standard_rate_to_mass_rate(
        self, standard_rate_m3_per_day: float | NDArray[np.float64]
    ) -> float | NDArray[np.float64]:
        """Convert standard volumetric rate to mass rate.

        Args:
            standard_rate_m3_per_day: Volumetric flow rate at standard conditions [Sm3/day]

        Returns:
            Mass flow rate [kg/h]
        """
        standard_density = self.fluid_properties.standard_density
        mass_rate_kg_per_hour = standard_rate_m3_per_day * standard_density / UnitConstants.HOURS_PER_DAY
        if isinstance(mass_rate_kg_per_hour, np.ndarray):
            return np.array(mass_rate_kg_per_hour)
        return float(mass_rate_kg_per_hour)

    def mass_rate_to_standard_rate(
        self, mass_rate_kg_per_h: float | NDArray[np.float64]
    ) -> float | NDArray[np.float64]:
        """Convert mass rate to standard volumetric rate.

        Args:
            mass_rate_kg_per_h: Mass flow rate [kg/h]

        Returns:
            Volumetric flow rate at standard conditions [Sm3/day]
        """
        standard_density = self.fluid_properties.standard_density
        standard_rate = mass_rate_kg_per_h / standard_density * UnitConstants.HOURS_PER_DAY
        if isinstance(standard_rate, np.ndarray):
            return np.array(standard_rate)
        return float(standard_rate)

    # =========================================================================
    # Backwards compatibility methods - these will be deprecated
    # =========================================================================

    @classmethod
    def from_fluid_model(cls, fluid_model: FluidModel) -> NeqSimFluidFactory:
        """Create a lazy fluid factory from a fluid model.

        This method provides backwards compatibility for the old constructor pattern.
        The factory is created without computing properties - they are computed
        lazily on first access.

        Args:
            fluid_model: The fluid model (composition + EoS)

        Returns:
            A new NeqSimFluidFactory (lazy - properties computed on first access)
        """
        return cls(fluid_model=fluid_model, _fluid_properties=None)

    def get_properties(
        self, pressure_bara: float, temperature_kelvin: float, remove_liquid: bool = False
    ) -> FluidProperties:
        """Get fluid properties at specified conditions.

        DEPRECATED: Use flash_pt() instead.

        Args:
            pressure_bara: Pressure in bara
            temperature_kelvin: Temperature in Kelvin
            remove_liquid: Whether to remove liquid phase (default False)

        Returns:
            FluidProperties at the specified conditions
        """
        return self.flash_pt(pressure_bara, temperature_kelvin, remove_liquid).fluid_properties

    def create_stream_from_standard_rate(
        self, pressure_bara: float, temperature_kelvin: float, standard_rate_m3_per_day: float
    ):
        """Create a fluid stream from standard volumetric rate.

        DEPRECATED: Use flash_pt().to_stream() instead.

        Args:
            pressure_bara: Pressure in bara
            temperature_kelvin: Temperature in Kelvin
            standard_rate_m3_per_day: Volumetric flow rate at standard conditions [Sm3/day]

        Returns:
            A FluidStream instance
        """
        return self.flash_pt(pressure_bara, temperature_kelvin).to_stream(
            standard_rate_m3_per_day=standard_rate_m3_per_day
        )

    def create_stream_from_mass_rate(
        self, pressure_bara: float, temperature_kelvin: float, mass_rate_kg_per_h: float
    ):
        """Create a fluid stream from mass rate.

        DEPRECATED: Use flash_pt().to_stream() instead.

        Args:
            pressure_bara: Pressure in bara
            temperature_kelvin: Temperature in Kelvin
            mass_rate_kg_per_h: Mass flow rate [kg/h]

        Returns:
            A FluidStream instance
        """
        return self.flash_pt(pressure_bara, temperature_kelvin).to_stream(
            mass_rate_kg_per_h=mass_rate_kg_per_h
        )

    def create_fluid_factory_from_fluid_model(self, fluid_model: FluidModel) -> NeqSimFluidFactory:
        """Create a new fluid factory from a fluid model.

        DEPRECATED: Use NeqSimFluidFactory.from_fluid_model() instead.

        Args:
            fluid_model: The fluid model to use for the new factory

        Returns:
            A new NeqSimFluidFactory instance (lazy)
        """
        return NeqSimFluidFactory.from_fluid_model(fluid_model)
