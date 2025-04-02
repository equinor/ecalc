from __future__ import annotations

from functools import cached_property
from typing import Protocol

from ecalc_neqsim_wrapper.thermo import NeqsimFluid
from libecalc.common.fluid import EoSModel, FluidComposition
from libecalc.domain.process.core.stream.conditions import ProcessConditions


class ThermoSystemInterface(Protocol):
    """
    Defines the core thermodynamic interface for a single fluid state
    at specified conditions (pressure, temperature).

    Properties correspond to the ones currently used in Stream:
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


class NeqSimThermoSystem:
    """
    Implementation of ThermoSystemInterface for NeqSim.
    Maintains a single 'live' NeqsimFluid object for the composition & EoS
    at specified conditions (pressure, temperature).
    """

    def __init__(
        self,
        composition: FluidComposition,
        eos_model: EoSModel,
        conditions: ProcessConditions,
        neqsim_fluid: NeqsimFluid | None = None,
    ):
        # Normalize composition to ensure it sums to 1
        self._composition = composition.normalized()
        self._eos_model = eos_model
        self._conditions = conditions

        if neqsim_fluid is not None:
            self._neqsim_fluid = neqsim_fluid
        else:
            self._neqsim_fluid = NeqsimFluid.create_thermo_system(
                composition=self._composition,
                temperature_kelvin=self.temperature_kelvin,
                pressure_bara=self.pressure_bara,
                eos_model=self._eos_model,
            )

    def __setattr__(self, name, value):
        """Prevent modification of attributes after initialization."""
        if hasattr(self, name):
            raise AttributeError(f"Cannot modify attribute '{name}' - NeqSimThermoSystem is immutable")
        super().__setattr__(name, value)

    @property
    def composition(self) -> FluidComposition:
        return self._composition

    @property
    def eos_model(self) -> EoSModel:
        return self._eos_model

    @property
    def conditions(self) -> ProcessConditions:
        return self._conditions

    @property
    def pressure_bara(self) -> float:
        return self._conditions.pressure_bara

    @property
    def temperature_kelvin(self) -> float:
        return self._conditions.temperature_kelvin

    @cached_property
    def density(self) -> float:
        return self._neqsim_fluid.density

    @cached_property
    def enthalpy(self) -> float:
        return self._neqsim_fluid.enthalpy_joule_per_kg

    @cached_property
    def z(self) -> float:
        return self._neqsim_fluid.z

    @cached_property
    def kappa(self) -> float:
        return self._neqsim_fluid.kappa

    @cached_property
    def standard_density_gas_phase_after_flash(self) -> float:
        """Get gas phase density at standard conditions after TP flash and liquid removal [kg/Sm³]."""
        # Create fluid at standard conditions using a clone to avoid modifying the main fluid
        standard_conditions = ProcessConditions.standard_conditions()
        cloned_fluid = self._neqsim_fluid.copy()
        stripped_fluid: NeqsimFluid = cloned_fluid.set_new_pressure_and_temperature(
            new_pressure_bara=standard_conditions.pressure_bara,
            new_temperature_kelvin=standard_conditions.temperature_kelvin,
            remove_liquid=True,
        )
        return stripped_fluid.density

    @cached_property
    def vapor_fraction_molar(self) -> float:
        return self._neqsim_fluid.vapor_fraction_molar

    @cached_property
    def molar_mass(self) -> float:
        return self._neqsim_fluid.molar_mass

    def flash_to_conditions(self, conditions: ProcessConditions, remove_liquid: bool = True) -> NeqSimThermoSystem:
        """
        Clone our existing _neqsim_fluid, set new conditions, skip re-add of components,
        and return a *new* NeqSimThermoSystem object.

        Args:
            conditions: New process conditions (pressure and temperature)
            remove_liquid: Whether to remove liquid phase after flash calculation

        Returns:
            A new NeqSimThermoSystem with updated conditions
        """
        updated_fluid = self._neqsim_fluid.set_new_pressure_and_temperature(
            new_pressure_bara=conditions.pressure_bara,
            new_temperature_kelvin=conditions.temperature_kelvin,
            remove_liquid=remove_liquid,
        )

        # Get updated composition if liquid is removed, otherwise keep the original
        composition = updated_fluid.composition if remove_liquid else self._composition

        return NeqSimThermoSystem(
            composition=composition,
            eos_model=self._eos_model,
            conditions=conditions,
            neqsim_fluid=updated_fluid,
        )

    def flash_to_pressure_and_enthalpy_change(
        self, pressure_bara: float, enthalpy_change: float, remove_liquid: bool = True
    ) -> NeqSimThermoSystem:
        """
        Clone our existing _neqsim_fluid, update using a PH flash (pressure and enthalpy),
        and return a *new* NeqSimThermoSystem object.

        Args:
            pressure_bara: New pressure [bara]
            enthalpy_change: Change in specific enthalpy [J/kg]
            remove_liquid: Whether to remove liquid phase after flash calculation

        Returns:
            A new NeqSimThermoSystem with updated conditions
        """
        original_enthalpy_joule_per_kg = self._neqsim_fluid.enthalpy_joule_per_kg
        updated_fluid = self._neqsim_fluid.set_new_pressure_and_enthalpy(
            new_pressure=pressure_bara,
            new_enthalpy_joule_per_kg=original_enthalpy_joule_per_kg + enthalpy_change,
            remove_liquid=remove_liquid,
        )

        # Get updated composition if liquid is removed, otherwise keep the original
        composition = updated_fluid.composition if remove_liquid else self._composition

        # Create new conditions with the resulting temperature
        new_conditions = ProcessConditions(
            pressure_bara=pressure_bara,
            temperature_kelvin=updated_fluid.temperature_kelvin,
        )

        return NeqSimThermoSystem(
            composition=composition,
            eos_model=self._eos_model,
            conditions=new_conditions,
            neqsim_fluid=updated_fluid,
        )
