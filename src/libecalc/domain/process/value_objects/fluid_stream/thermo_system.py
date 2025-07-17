from __future__ import annotations

from functools import cached_property
from typing import Protocol

from libecalc.domain.process.value_objects.fluid_stream.fluid_model import EoSModel, FluidComposition
from libecalc.domain.process.value_objects.fluid_stream.process_conditions import ProcessConditions


class ThermoSystemInterface(Protocol):
    """
    Defines the core thermodynamic interface for a single fluid state
    at specified conditions (pressure, temperature).

    Properties correspond to the ones currently used in FluidStream:
      - composition         [FluidComposition]
      - eos_model          [EoSModel]
      - conditions         [ProcessConditions]
      - molar_mass         [kg/mol]
      - pressure_bara      [bara]
      - temperature_kelvin  [K]
      - density            [kg/m³]
      - enthalpy           [J/kg]
      - z                  [-]
      - kappa              [-]
      - standard_density_gas_phase_after_flash [kg/Sm³]
      - vapor_fraction_molar                  [mol fraction, 0-1]
    """

    @property
    def conditions(self) -> ProcessConditions: ...

    @property
    def pressure_bara(self) -> float: ...

    @property
    def temperature_kelvin(self) -> float: ...

    @property
    def composition(self) -> FluidComposition:
        """Get the fluid composition"""
        ...

    @property
    def eos_model(self) -> EoSModel:
        """Get the equation of state model used"""
        ...

    @cached_property
    def density(self) -> float: ...

    @cached_property
    def enthalpy(self) -> float: ...

    @cached_property
    def z(self) -> float: ...

    @cached_property
    def kappa(self) -> float: ...

    @cached_property
    def standard_density_gas_phase_after_flash(self) -> float: ...

    @cached_property
    def vapor_fraction_molar(self) -> float: ...

    @cached_property
    def molar_mass(self) -> float: ...

    def flash_to_conditions(self, conditions: ProcessConditions, remove_liquid: bool = True) -> ThermoSystemInterface:
        """
        Return a new ThermoSystemInterface with updated conditions,
        reusing the same composition/EoS and skipping re-add of components.

        Args:
            conditions: New process conditions (pressure and temperature)
            remove_liquid: Whether to remove liquid phase after flash calculation

        Returns:
            A new ThermoSystemInterface with updated conditions
        """
        ...

    def flash_to_pressure_and_enthalpy_change(
        self, pressure_bara: float, enthalpy_change: float, remove_liquid: bool = True
    ) -> ThermoSystemInterface:
        """
        Return a new ThermoSystemInterface with updated pressure and changed enthalpy,
        reusing the same composition/EoS and skipping re-add of components.

        This simulates a PH-flash operation.

        Args:
            pressure_bara: New pressure [bara]
            enthalpy_change: Change in specific enthalpy [J/kg]
            remove_liquid: Whether to remove liquid phase after flash calculation

        Returns:
            A new ThermoSystemInterface with updated conditions
        """
        ...
