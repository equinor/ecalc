from __future__ import annotations

import os
from functools import cached_property

from ecalc_neqsim_wrapper.cache_service import CacheService
from ecalc_neqsim_wrapper.thermo import NeqsimFluid
from libecalc.domain.process.value_objects.fluid_stream.fluid_model import EoSModel, FluidComposition, FluidModel
from libecalc.domain.process.value_objects.fluid_stream.process_conditions import ProcessConditions
from libecalc.domain.process.value_objects.fluid_stream.thermo_system import ThermoSystemInterface

# NOTE: Cached NeqSimThermoSystem objects hold references to JVM objects via py4j.
# Cache lifetime must not exceed JVM session lifetime. CacheService.clear_all()
# is called automatically when the JVM service shuts down to prevent dangling references.

# Configurable cache size via environment variable
_CACHE_MAX_SIZE = int(os.getenv("ECALC_FLASH_CACHE_MAX_SIZE", "10000"))

# Per-property decimal tolerance for cache key rounding (cache optimization)
# These constants should balance cache hit rates with acceptable precision for eCalc calculations
_PRESSURE_DECIMALS = 3  # 0.001 bara = 1 mbar precision
_TEMPERATURE_DECIMALS = 2  # 0.01 K precision
_ENTHALPY_DECIMALS = 1  # 0.1 J/kg precision

# Create flash cache via CacheService for automatic cleanup on JVM shutdown
_FLASH_CACHE = CacheService.create_cache("thermo_flash", max_size=_CACHE_MAX_SIZE)


def clear_thermo_flash_cache() -> None:
    """Clear the flash cache. Useful for debugging tests and memory management."""
    CacheService.clear_cache("thermo_flash")


def get_flash_cache_stats() -> dict[str, int | float]:
    """Get cache statistics for monitoring and debugging."""
    return _FLASH_CACHE.get_stats()


class NeqSimThermoSystem(ThermoSystemInterface):
    """
    Implementation of ThermoSystemInterface for NeqSim.
    Maintains a single 'live' NeqsimFluid object for the composition & EoS
    at specified conditions (pressure, temperature).
    """

    def __init__(
        self,
        fluid_model: FluidModel,
        conditions: ProcessConditions,
        neqsim_fluid: NeqsimFluid | None = None,
    ):
        # Normalize composition to ensure it sums to 1
        self._composition = fluid_model.composition.normalized()
        self._eos_model = fluid_model.eos_model
        self._conditions = conditions

        if neqsim_fluid is not None:
            self._neqsim_fluid = neqsim_fluid
        else:
            # Note: this will flash the system to the specified conditions
            self._neqsim_fluid = NeqsimFluid.create_thermo_system(
                composition=self._composition,
                temperature_kelvin=self.temperature_kelvin,
                pressure_bara=self.pressure_bara,
                eos_model=self._eos_model,
            )

    def __setattr__(self, name, value):
        """Prevent modification of attributes after initialization (important for caching)."""
        if hasattr(self, name):
            raise AttributeError(f"Cannot modify attribute '{name}' - NeqSimThermoSystem is immutable")
        super().__setattr__(name, value)

    @property
    def composition(self) -> FluidComposition:
        return self._composition

    @cached_property
    def _composition_cache_key(self) -> tuple:
        """Cached serialized composition tuple for use in cache keys.

        Computing tuple(sorted(composition.model_dump().items())) is expensive,
        so we cache it once per instance to avoid repeated serialization.
        This is safe because composition is immutable.
        """
        return tuple(sorted(self._composition.model_dump().items()))

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
        # Cache key with rounded floats and cached composition tuple
        cache_key = (
            "TP",
            self._composition_cache_key,  # Cached property avoids repeated model_dump()
            self._eos_model,
            round(conditions.pressure_bara, _PRESSURE_DECIMALS),
            round(conditions.temperature_kelvin, _TEMPERATURE_DECIMALS),
            remove_liquid,
        )

        cached = _FLASH_CACHE.get(cache_key)
        if cached is not None:
            return cached

        updated_fluid = self._neqsim_fluid.set_new_pressure_and_temperature(
            new_pressure_bara=conditions.pressure_bara,
            new_temperature_kelvin=conditions.temperature_kelvin,
            remove_liquid=remove_liquid,
        )

        # Get updated composition if liquid is removed, otherwise keep the original
        composition = updated_fluid.composition if remove_liquid else self._composition

        # Create a new fluid model with the updated composition
        updated_fluid_model = FluidModel(
            composition=composition,
            eos_model=self._eos_model,
        )

        result = NeqSimThermoSystem(
            fluid_model=updated_fluid_model,
            conditions=conditions,
            neqsim_fluid=updated_fluid,
        )

        _FLASH_CACHE.put(cache_key, result)

        return result

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
        target_enthalpy = original_enthalpy_joule_per_kg + enthalpy_change

        # Cache key with rounded floats and cached composition tuple
        cache_key = (
            "PH",
            self._composition_cache_key,  # Cached property avoids repeated model_dump()
            self._eos_model,
            round(pressure_bara, _PRESSURE_DECIMALS),
            round(target_enthalpy, _ENTHALPY_DECIMALS),
            remove_liquid,
        )

        cached = _FLASH_CACHE.get(cache_key)
        if cached is not None:
            return cached

        updated_fluid = self._neqsim_fluid.set_new_pressure_and_enthalpy(
            new_pressure=pressure_bara,
            new_enthalpy_joule_per_kg=target_enthalpy,
            remove_liquid=remove_liquid,
        )

        # Get updated composition if liquid is removed, otherwise keep the original
        composition = updated_fluid.composition if remove_liquid else self._composition

        # Create new conditions with the resulting temperature
        new_conditions = ProcessConditions(
            pressure_bara=pressure_bara,
            temperature_kelvin=updated_fluid.temperature_kelvin,
        )

        # Create a new fluid model with the updated composition
        updated_fluid_model = FluidModel(
            composition=composition,
            eos_model=self._eos_model,
        )

        result = NeqSimThermoSystem(
            fluid_model=updated_fluid_model,
            conditions=new_conditions,
            neqsim_fluid=updated_fluid,
        )

        _FLASH_CACHE.put(cache_key, result)

        return result
