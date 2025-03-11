from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from typing import Literal, Optional, Protocol

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

    There are two ways to create a Fluid instance:
    1. Using the default constructor: Fluid(composition=...)
       - creates a fluid with NeqSim engine (default)
    2. Using the factory method: Fluid.with_neqsim_engine(composition=...)
       - explicitly creates a fluid with NeqSim engine
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
        from libecalc.domain.process.core.stream.thermo_adapters import NeqSimThermodynamicAdapter

        # Use object.__setattr__ since this is a frozen dataclass
        if self._engine_type == "neqsim":
            # For NeqSim, we require an EoS model
            if self.eos_model is None:
                # Default to SRK if not specified
                object.__setattr__(self, "eos_model", self.DEFAULT_EOS_MODEL)
            engine = NeqSimThermodynamicAdapter()
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
    def with_neqsim_engine(cls, composition: FluidComposition, eos_model: Optional[EoSModel] = None) -> Fluid:
        """Create a fluid instance that uses the NeqSim engine"""
        return cls(composition=composition, eos_model=eos_model, _engine_type="neqsim")
