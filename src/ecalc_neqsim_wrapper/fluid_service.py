"""Centralized service for all NeqSim thermodynamic operations with global caching.

This service provides a singleton pattern with global caches for:
- Reference NeqsimFluid instances (by composition + EoS)
- Flash results (TP and PH flashes)

The caches are automatically cleared when the JVM shuts down via CacheService.
"""

from __future__ import annotations

import os
from typing import ClassVar

import numpy as np

from ecalc_neqsim_wrapper.cache_service import CacheService, LRUCache
from ecalc_neqsim_wrapper.thermo import NeqsimFluid
from libecalc.domain.process.value_objects.fluid_stream.fluid import Fluid
from libecalc.domain.process.value_objects.fluid_stream.fluid_model import EoSModel, FluidComposition, FluidModel
from libecalc.domain.process.value_objects.fluid_stream.fluid_properties import FluidProperties
from libecalc.domain.process.value_objects.fluid_stream.fluid_service import FluidServiceInterface
from libecalc.domain.process.value_objects.fluid_stream.fluid_stream import FluidStream

# Configurable cache sizes via environment variables
# Reference cache needs to be large enough to hold all unique compositions to avoid evictions
_REFERENCE_CACHE_MAX_SIZE = int(os.getenv("ECALC_REFERENCE_CACHE_MAX_SIZE", "512"))
_FLASH_CACHE_MAX_SIZE = int(os.getenv("ECALC_FLASH_CACHE_MAX_SIZE", "10000"))

# Rounding constants for cache keys (match existing flash cache precision)
_PRESSURE_DECIMALS = 3  # 0.001 bara = 1 mbar precision
_TEMPERATURE_DECIMALS = 2  # 0.01 K precision
_ENTHALPY_DECIMALS = 1  # 0.1 J/kg precision
_COMPOSITION_DECIMALS = 8  # 1e-8 precision for mole fractions

# Standard conditions for reference fluids and standard density calculations
_STANDARD_TEMPERATURE_KELVIN = 288.15
_STANDARD_PRESSURE_BARA = 1.01325


def _make_composition_key(composition: FluidComposition) -> tuple:
    """Create hashable cache key from composition with some rounding for cache effectiveness.

    Rounds mole fractions to avoid floating point differences causing cache misses.
    """
    return tuple((k, round(v, _COMPOSITION_DECIMALS)) for k, v in sorted(composition.model_dump().items()))


class NeqSimFluidService(FluidServiceInterface):
    """Centralized service for all thermodynamic operations with global caching.

    This singleton service manages:
    - Reference cache: Stores NeqsimFluid instances at standard conditions per (composition, eos_model)
    - Flash cache: Stores FluidProperties results for TP and PH flash operations

    Usage:
        service = NeqSimFluidService.instance()
        props, composition = service.flash_pt(fluid_model, pressure_bara, temperature_kelvin)
        props, composition = service.flash_ph(fluid_model, pressure_bara, target_enthalpy)
    """

    _instance: ClassVar[NeqSimFluidService | None] = None

    def __init__(self) -> None:
        """Initialize the service with reference and flash caches."""
        # Reference cache: stores NeqsimFluid at standard conditions (~50-100 unique compositions)
        self._reference_cache: LRUCache = CacheService.create_cache(
            "reference_fluid", max_size=_REFERENCE_CACHE_MAX_SIZE
        )
        # Flash cache: stores FluidProperties for TP/PH flash results
        self._flash_cache: LRUCache = CacheService.create_cache("fluid_service_flash", max_size=_FLASH_CACHE_MAX_SIZE)

    @classmethod
    def instance(cls) -> NeqSimFluidService:
        """Get the singleton instance of the service."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance. Useful for testing."""
        cls._instance = None

    def _get_reference_fluid(self, fluid_model: FluidModel) -> NeqsimFluid:
        """Get or create reference NeqsimFluid at standard conditions.

        Reference fluids are cached by (composition, eos_model) and created at
        standard conditions. All flash operations start from these references.
        """
        composition = fluid_model.composition.normalized()
        key = (_make_composition_key(composition), fluid_model.eos_model)

        cached = self._reference_cache.get(key)
        if cached is not None:
            return cached

        ref = NeqsimFluid.create_thermo_system(
            composition=composition,
            temperature_kelvin=_STANDARD_TEMPERATURE_KELVIN,
            pressure_bara=_STANDARD_PRESSURE_BARA,
            eos_model=fluid_model.eos_model,
        )
        self._reference_cache.put(key, ref)
        return ref

    def _make_pt_cache_key(
        self, composition_key: tuple, eos_model: EoSModel, pressure: float, temperature: float
    ) -> tuple:
        """Create cache key for TP flash with proper rounding.

        Note: remove_liquid is NOT part of the key - we always cache base flash results.
        """
        return (
            "TP",
            composition_key,
            eos_model,
            round(pressure, _PRESSURE_DECIMALS),
            round(temperature, _TEMPERATURE_DECIMALS),
        )

    def _make_ph_cache_key(
        self, composition_key: tuple, eos_model: EoSModel, pressure: float, target_enthalpy: float
    ) -> tuple:
        """Create cache key for PH flash with proper rounding.

        Note: remove_liquid is NOT part of the key - we always cache base flash results.
        """
        return (
            "PH",
            composition_key,
            eos_model,
            round(pressure, _PRESSURE_DECIMALS),
            round(target_enthalpy, _ENTHALPY_DECIMALS),
        )

    def _get_standard_density(self, fluid_model: FluidModel) -> float:
        """Get gas-phase density at standard conditions.

        The reference fluid is already at standard conditions, so we just
        return its density directly. This avoids redundant flash operations
        and flash cache pollution.

        Note: density is a @cached_property on NeqsimFluid, so accessing ref.density
        doesn't trigger additional JVM calls for cached reference fluids.
        """
        ref = self._get_reference_fluid(fluid_model)

        # Reference is at standard conditions - return density directly
        # For gases, vapor_fraction should be ~1.0 at standard conditions
        if ref.vapor_fraction_molar >= 0.9999:
            return ref.density

        # Rare case: liquid present at standard conditions - remove it
        flashed = ref.set_new_pressure_and_temperature(
            new_pressure_bara=_STANDARD_PRESSURE_BARA,
            new_temperature_kelvin=_STANDARD_TEMPERATURE_KELVIN,
            remove_liquid=True,
        )
        return flashed.density

    def _extract_properties(
        self, neqsim_fluid: NeqsimFluid, composition: FluidComposition, fluid_model: FluidModel
    ) -> FluidProperties:
        """Extract all properties from NeqsimFluid into pure dataclass.

        Args:
            neqsim_fluid: The NeqsimFluid to extract properties from
            composition: The composition to use for molar_mass calculation (may differ from
                fluid_model.composition when liquid has been removed)
            fluid_model: The original fluid model (used for standard_density calculation)

        Note: molar_mass is calculated from the provided composition, which may be the
        gas-phase composition after liquid removal.
        """
        return FluidProperties(
            temperature_kelvin=neqsim_fluid.temperature_kelvin,
            pressure_bara=neqsim_fluid.pressure_bara,
            density=neqsim_fluid.density,
            enthalpy_joule_per_kg=neqsim_fluid.enthalpy_joule_per_kg,
            z=neqsim_fluid.z,
            kappa=neqsim_fluid.kappa,
            vapor_fraction_molar=neqsim_fluid.vapor_fraction_molar,
            molar_mass=composition.molar_mass_mixture,
            standard_density=self._get_standard_density(fluid_model),
        )

    def flash_pt(
        self,
        fluid_model: FluidModel,
        pressure_bara: float,
        temperature_kelvin: float,
        remove_liquid: bool = False,
    ) -> tuple[FluidProperties, FluidComposition]:
        """TP flash returning properties and composition.

        Args:
            fluid_model: The fluid model (composition + EoS)
            pressure_bara: Target pressure in bara
            temperature_kelvin: Target temperature in Kelvin
            remove_liquid: Whether to remove liquid phase after flash

        Returns:
            Tuple of (FluidProperties, FluidComposition) where composition may be
            updated to gas-phase composition if remove_liquid=True and liquid was present.
        """
        composition = fluid_model.composition.normalized()
        composition_key = _make_composition_key(composition)
        cache_key = self._make_pt_cache_key(composition_key, fluid_model.eos_model, pressure_bara, temperature_kelvin)

        # Check cache first (always stores base flash without liquid removal)
        cached = self._flash_cache.get(cache_key)
        if cached is not None:
            # If no liquid removal needed or fluid is already vapor, use cached result
            if not remove_liquid or cached.vapor_fraction_molar >= 0.9999:
                return (cached, composition)
            # Otherwise need to recompute with liquid removal (rare case)

        ref = self._get_reference_fluid(fluid_model)
        flashed = ref.set_new_pressure_and_temperature(
            new_pressure_bara=pressure_bara,
            new_temperature_kelvin=temperature_kelvin,
            remove_liquid=remove_liquid,
        )

        # Get updated composition if liquid was removed
        if remove_liquid and flashed.vapor_fraction_molar < 0.9999:
            # Liquid was present and removed - get gas-phase composition from NeqSim
            updated_composition = flashed.composition
        else:
            # No liquid removal or already all vapor - composition unchanged
            updated_composition = composition

        result = self._extract_properties(flashed, updated_composition, fluid_model)
        # Only cache base flash results (remove_liquid=False) to avoid polluting cache
        if not remove_liquid:
            self._flash_cache.put(cache_key, result)
        return (result, updated_composition)

    def flash_ph(
        self,
        fluid_model: FluidModel,
        pressure_bara: float,
        target_enthalpy: float,
        remove_liquid: bool = False,
    ) -> tuple[FluidProperties, FluidComposition]:
        """PH flash to target pressure and enthalpy.

        Args:
            fluid_model: The fluid model (composition + EoS)
            pressure_bara: Target pressure in bara
            target_enthalpy: Target specific enthalpy in J/kg
            remove_liquid: Whether to remove liquid phase after flash

        Returns:
            Tuple of (FluidProperties, FluidComposition) where composition may be
            updated to gas-phase composition if remove_liquid=True and liquid was present.
        """
        composition = fluid_model.composition.normalized()
        composition_key = _make_composition_key(composition)
        cache_key = self._make_ph_cache_key(composition_key, fluid_model.eos_model, pressure_bara, target_enthalpy)

        # Check cache first (always stores base flash without liquid removal)
        cached = self._flash_cache.get(cache_key)
        if cached is not None:
            # If no liquid removal needed or fluid is already vapor, use cached result
            if not remove_liquid or cached.vapor_fraction_molar >= 0.9999:
                return (cached, composition)
            # Otherwise need to recompute with liquid removal (rare case)

        ref = self._get_reference_fluid(fluid_model)
        flashed = ref.set_new_pressure_and_enthalpy(
            new_pressure=pressure_bara,
            new_enthalpy_joule_per_kg=target_enthalpy,
            remove_liquid=remove_liquid,
        )

        # Get updated composition if liquid was removed
        if remove_liquid and flashed.vapor_fraction_molar < 0.9999:
            # Liquid was present and removed - get gas-phase composition from NeqSim
            updated_composition = flashed.composition
        else:
            # No liquid removal or already all vapor - composition unchanged
            updated_composition = composition

        result = self._extract_properties(flashed, updated_composition, fluid_model)
        # Only cache base flash results (remove_liquid=False) to avoid polluting cache
        if not remove_liquid:
            self._flash_cache.put(cache_key, result)
        return (result, updated_composition)

    # === Factory Methods (implementing FluidServiceInterface) ===

    def create_fluid(
        self,
        fluid_model: FluidModel,
        pressure_bara: float,
        temperature_kelvin: float,
        remove_liquid: bool = False,
    ) -> Fluid:
        """Create a Fluid at specified conditions via TP flash.

        Args:
            fluid_model: The fluid model (composition + EoS)
            pressure_bara: Target pressure in bara
            temperature_kelvin: Target temperature in Kelvin
            remove_liquid: Whether to remove liquid phase after flash

        Returns:
            New Fluid instance at the specified conditions.
        """
        props, new_composition = self.flash_pt(fluid_model, pressure_bara, temperature_kelvin, remove_liquid)
        new_fluid_model = FluidModel(composition=new_composition, eos_model=fluid_model.eos_model)
        return Fluid(fluid_model=new_fluid_model, properties=props)

    def create_stream_from_standard_rate(
        self,
        fluid_model: FluidModel,
        pressure_bara: float,
        temperature_kelvin: float,
        standard_rate_m3_per_day: float,
    ) -> FluidStream:
        """Create a fluid stream from standard volumetric rate.

        Args:
            fluid_model: The fluid model (composition + EoS)
            pressure_bara: Target pressure in bara
            temperature_kelvin: Target temperature in Kelvin
            standard_rate_m3_per_day: Volumetric flow rate at standard conditions [Sm3/day]

        Returns:
            A FluidStream instance
        """
        fluid = self.create_fluid(fluid_model, pressure_bara, temperature_kelvin)
        mass_rate = float(self.standard_rate_to_mass_rate(fluid_model, standard_rate_m3_per_day))
        return FluidStream(fluid=fluid, mass_rate_kg_per_h=mass_rate)

    def create_stream_from_mass_rate(
        self,
        fluid_model: FluidModel,
        pressure_bara: float,
        temperature_kelvin: float,
        mass_rate_kg_per_h: float,
    ) -> FluidStream:
        """Create a fluid stream from mass rate.

        Args:
            fluid_model: The fluid model (composition + EoS)
            pressure_bara: Target pressure in bara
            temperature_kelvin: Target temperature in Kelvin
            mass_rate_kg_per_h: Mass flow rate [kg/h]

        Returns:
            A FluidStream instance
        """
        fluid = self.create_fluid(fluid_model, pressure_bara, temperature_kelvin)
        return FluidStream(fluid=fluid, mass_rate_kg_per_h=mass_rate_kg_per_h)

    def standard_rate_to_mass_rate(
        self,
        fluid_model: FluidModel,
        standard_rate_m3_per_day: float,
    ) -> float:
        """Convert standard volumetric rate to mass rate (kg/h).

        Args:
            fluid_model: The fluid model (composition + EoS)
            standard_rate_m3_per_day: Volumetric flow rate at standard conditions [Sm3/day]

        Returns:
            Mass flow rate [kg/h]
        """
        standard_density = self._get_standard_density(fluid_model)
        result = standard_rate_m3_per_day * standard_density / 24.0
        if isinstance(result, np.ndarray):
            return np.array(result)
        return float(result)

    def mass_rate_to_standard_rate(
        self,
        fluid_model: FluidModel,
        mass_rate_kg_per_h: float,
    ) -> float:
        """Convert mass rate (kg/h) to standard volumetric rate (Sm3/day).

        Args:
            fluid_model: The fluid model (composition + EoS)
            mass_rate_kg_per_h: Mass flow rate [kg/h]

        Returns:
            Volumetric flow rate at standard conditions [Sm3/day]
        """
        standard_density = self._get_standard_density(fluid_model)
        result = mass_rate_kg_per_h * 24.0 / standard_density
        if isinstance(result, np.ndarray):
            return np.array(result)
        return float(result)


def get_fluid_service_stats() -> dict[str, dict]:
    """Get cache statistics for the fluid service caches."""
    ref_cache = CacheService.get_cache("reference_fluid")
    flash_cache = CacheService.get_cache("fluid_service_flash")
    return {
        "reference_fluid": ref_cache.get_stats() if ref_cache else {},
        "fluid_service_flash": flash_cache.get_stats() if flash_cache else {},
    }
