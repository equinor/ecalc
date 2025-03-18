from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from typing import Literal, Protocol

from libecalc.common.fluid import EoSModel, FluidComposition


class ThermodynamicEngine(Protocol):
    """Protocol defining the interface for thermodynamic calculations"""

    def get_density(self, fluid: Fluid, *, pressure: float, temperature: float) -> float:
        """Get density at given conditions [kg/m³]"""
        ...

    def get_enthalpy(self, fluid: Fluid, *, pressure: float, temperature: float) -> float:
        """Get specific enthalpy at given conditions [kJ/kg]"""
        ...

    def get_z(self, fluid: Fluid, *, pressure: float, temperature: float) -> float:
        """Get compressibility factor at given conditions [-]"""
        ...

    def get_kappa(self, fluid: Fluid, *, pressure: float, temperature: float) -> float:
        """Get isentropic exponent at given conditions [-]"""
        ...

    def get_standard_density_gas_phase_after_flash(self, fluid: Fluid) -> float:
        """Get gas phase density at standard conditions after TP flash [kg/Sm³]"""
        ...

    def get_vapor_fraction_molar(self, fluid: Fluid, *, pressure: float, temperature: float) -> float:
        """Get molar vapor fraction at given conditions [0-1]"""
        ...

    def get_molar_mass(self, fluid: Fluid) -> float:
        """Get molar mass of the fluid [kg/mol]"""
        ...


# Define a type for supported thermodynamic engines
ThermodynamicEngineType = Literal["neqsim"]


@dataclass(frozen=True)
class Fluid:
    """
    Represents a fluid with composition and properties.

    This class abstracts away the specific implementation of thermodynamic
    calculations, allowing for different backends (NeqSim, explicit correlations, etc).

    Use fluid_factory to create instances of this class.
    """

    # Instance variables
    composition: FluidComposition
    _thermodynamic_engine: ThermodynamicEngine
    eos_model: EoSModel | None = None

    @cached_property
    def molar_mass(self) -> float:
        """Get molar mass of fluid [kg/mol]"""
        return self._thermodynamic_engine.get_molar_mass(self)
