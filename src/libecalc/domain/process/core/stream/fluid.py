from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from typing import Literal, Optional, Protocol

from libecalc.common.fluid import EoSModel, FluidComposition


class ThermodynamicEngine(Protocol):
    """Protocol defining the interface for thermodynamic calculations"""

    def get_density(self, fluid: Fluid, pressure: float, temperature: float) -> float:
        """Get density at given conditions [kg/m³]"""
        ...

    def get_enthalpy(self, fluid: Fluid, pressure: float, temperature: float) -> float:
        """Get specific enthalpy at given conditions [kJ/kg]"""
        ...

    def get_z(self, fluid: Fluid, pressure: float, temperature: float) -> float:
        """Get compressibility factor (Z) at given conditions [-]"""
        ...

    def get_kappa(self, fluid: Fluid, pressure: float, temperature: float) -> float:
        """Get heat capacity ratio (kappa) at given conditions [-]"""
        ...

    def get_standard_density_gas_phase_after_flash(self, fluid: Fluid) -> float:
        """Get gas phase density at standard conditions after TP flash and liquid removal [kg/m³]"""
        ...

    def get_gas_fraction_molar(self, fluid: Fluid, pressure: float, temperature: float) -> float:
        """Get molar gas fraction at given conditions (0.0-1.0)"""
        ...

    def get_molar_mass(self, fluid: Fluid) -> float:
        """Get molar mass [kg/kmol]"""
        ...

    def pt_flash(self, fluid: Fluid, pressure: float, temperature: float) -> float:
        """
        Perform a pressure-temperature (PT) flash calculation on the fluid.

        Args:
            fluid: The fluid to perform the flash calculation on
            pressure: Pressure in bara
            temperature: Temperature in Kelvin

        Returns:
            Gas phase molar fraction (between 0.0 and 1.0)
        """
        ...


# Define a type for supported thermodynamic engines
ThermodynamicEngineType = Literal["neqsim", "explicit_correlation"]


@dataclass(frozen=True)
class Fluid:
    """
    Represents a fluid with composition and properties.

    This class abstracts away the specific implementation of thermodynamic
    calculations, allowing for different backends (NeqSim, explicit correlations, etc).

    There are four ways to create a Fluid instance:
    1. Using the default constructor with default engine: Fluid(composition=...)
       - creates a fluid with NeqSim engine (default)
    2. Using the default constructor with explicit engine type: Fluid(composition=..., _engine_type="explicit_correlation")
       - creates a fluid with simplified thermodynamics engine (no EoS)
    3. Using the factory method: Fluid.with_neqsim_engine(composition=...)
       - explicitly creates a fluid with NeqSim engine
    4. Using the factory method: Fluid.with_explicit_correlation_engine(composition=...)
       - creates a fluid with simplified thermodynamics engine (no EoS)
    """

    # Class variables
    DEFAULT_EOS_MODEL = EoSModel.SRK

    # Instance variables
    composition: FluidComposition
    eos_model: Optional[EoSModel] = None
    _engine_type: ThermodynamicEngineType = "neqsim"  # Default to NeqSim
    _thermodynamic_engine: Optional[ThermodynamicEngine] = None  # Will be initialized in __post_init__

    def __post_init__(self):
        """Initialize the thermodynamic engine if not provided"""
        # If engine is already provided, we don't need to create one
        if self._thermodynamic_engine is not None:
            return

        # Import adapters here to avoid circular import at runtime
        from libecalc.domain.process.core.stream.thermo_adapters import (
            ExplicitCorrelationThermodynamicAdapter,
            NeqSimThermodynamicAdapter,
        )

        # Use object.__setattr__ since this is a frozen dataclass
        if self._engine_type == "neqsim":
            # For NeqSim, we require an EoS model
            if self.eos_model is None:
                # Default to SRK if not specified
                object.__setattr__(self, "eos_model", self.DEFAULT_EOS_MODEL)
            engine = NeqSimThermodynamicAdapter()
        elif self._engine_type == "explicit_correlation":
            # For explicit correlations, we don't use EoS model
            if self.eos_model is not None:
                raise ValueError("EoS model should not be specified for explicit correlation engine")
            engine = ExplicitCorrelationThermodynamicAdapter()
        else:
            # Fallback to NeqSim if unknown engine type
            if self.eos_model is None:
                object.__setattr__(self, "eos_model", self.DEFAULT_EOS_MODEL)
            engine = NeqSimThermodynamicAdapter()

        object.__setattr__(self, "_thermodynamic_engine", engine)

    @cached_property
    def molar_mass(self) -> float:
        """Get molar mass of fluid [kg/mol]"""
        return self._get_thermodynamic_engine().get_molar_mass(self)

    def _get_thermodynamic_engine(self) -> ThermodynamicEngine:
        """Get the thermodynamic engine for this fluid"""
        return self._thermodynamic_engine

    @classmethod
    def with_explicit_correlation_engine(cls, composition: FluidComposition) -> Fluid:
        """Create a fluid instance that uses the explicit correlation engine"""
        return cls(composition=composition, eos_model=None, _engine_type="explicit_correlation")

    @classmethod
    def with_neqsim_engine(cls, composition: FluidComposition, eos_model: Optional[EoSModel] = None) -> Fluid:
        """Create a fluid instance that uses the NeqSim engine"""
        return cls(composition=composition, eos_model=eos_model, _engine_type="neqsim")
