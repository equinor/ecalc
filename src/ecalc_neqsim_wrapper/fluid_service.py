"""Centralized service for all NeqSim thermodynamic operations with global caching.

This service provides a singleton pattern with global caches for:
- Reference NeqsimFluid instances (by composition + EoS)
- Flash results (TP and PH flashes)

The caches are automatically cleared when the JVM shuts down via CacheService.
"""

from __future__ import annotations

import logging
from typing import ClassVar

from ecalc_neqsim_wrapper.cache_service import CacheConfig, CacheName, CacheService, LRUCache
from ecalc_neqsim_wrapper.thermo import NeqsimFluid
from libecalc.domain.process.value_objects.fluid_stream.constants import ThermodynamicConstants
from libecalc.domain.process.value_objects.fluid_stream.fluid import Fluid
from libecalc.domain.process.value_objects.fluid_stream.fluid_model import EoSModel, FluidComposition, FluidModel
from libecalc.domain.process.value_objects.fluid_stream.fluid_properties import FluidProperties
from libecalc.domain.process.value_objects.fluid_stream.fluid_service import FluidService
from libecalc.domain.process.value_objects.fluid_stream.fluid_stream import FluidStream

_logger = logging.getLogger(__name__)

# Rounding constants for cache keys (for floating point issues)
# Note: some performance can be gained by reducing decimals somewhat more (with negligible accuracy loss)
# But a study shows that most of the cache effectiveness is achieved with no/low rounding, so we keep these fairly tight
_PRESSURE_DECIMALS = 6
_TEMPERATURE_DECIMALS = 6
_ENTHALPY_DECIMALS = 6

# 1e-8 precision for mole fractions (keep high, its just for minor floating point issues)
_COMPOSITION_DECIMALS = 8

# Standard conditions for reference fluids and standard density calculations
_STANDARD_TEMPERATURE_KELVIN = 288.15
_STANDARD_PRESSURE_BARA = 1.01325


def _make_composition_key(composition: FluidComposition) -> tuple:
    """Create hashable cache key from composition with some rounding for cache effectiveness.

    Rounds mole fractions to avoid floating point differences causing cache misses.
    """
    return tuple((k, round(v, _COMPOSITION_DECIMALS)) for k, v in sorted(composition.model_dump().items()))


class NeqSimFluidService(FluidService):
    """Centralized service for all thermodynamic operations with global caching.

    This singleton service manages:
    - Reference cache: Stores NeqsimFluid instances at standard conditions per (composition, eos_model)
    - Flash cache: Stores FluidProperties results for TP and PH flash operations

    Usage:
        service = NeqSimFluidService.instance()
        props = service.flash_pt(fluid_model, pressure_bara, temperature_kelvin)
        props = service.flash_ph(fluid_model, pressure_bara, target_enthalpy)
    """

    _instance: ClassVar[NeqSimFluidService | None] = None
    _cache_config: ClassVar[CacheConfig | None] = None

    def __new__(cls):
        """Enforce singleton pattern by always returning the same instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def configure(cls, cache_config: CacheConfig) -> None:
        """Configure cache sizes before first use.

        Must be called BEFORE the first call to instance() or NeqSimFluidService().
        Configuration is applied when the singleton is created.

        Args:
            cache_config: Cache configuration with max sizes.

        Raises:
            RuntimeError: If called after singleton already exists.

        Example:
            # At application startup, before any model processing
            NeqSimFluidService.configure(CacheConfig(
                reference_fluid_max_size=100,
                flash_max_size=200_000,
            ))

            # Later, use normally
            with NeqsimService.factory().initialize():
                model = YamlModel(...)
                model.evaluate_energy_usage()
        """
        if cls._instance is not None:
            raise RuntimeError(
                "NeqSimFluidService.configure() must be called before the first "
                "instance() call. The singleton has already been created."
            )
        cls._cache_config = cache_config

    def __init__(self) -> None:
        """Initialize the service with reference and flash caches.

        Uses cache sizes from configure() if called, otherwise uses defaults.
        Logs the cache configuration for visibility.

        Note: Due to singleton enforcement in __new__, this is only executed once.
        Subsequent calls to NeqSimFluidService() return the existing instance.
        Prefer using NeqSimFluidService.instance() for clarity.
        """
        # Guard against re-initialization if __init__ is called multiple times
        if hasattr(self, "_initialized"):
            return
        self._initialized = True

        # Use configured sizes or defaults
        if self._cache_config is not None:
            config = self._cache_config
            _logger.info(
                f"NeqSimFluidService initialized with custom cache config: "
                f"reference_fluid_max_size={config.reference_fluid_max_size}, "
                f"flash_max_size={config.flash_max_size}"
            )
        else:
            config = CacheConfig.default()
            _logger.info(
                f"NeqSimFluidService initialized with default cache config: "
                f"reference_fluid_max_size={config.reference_fluid_max_size}, "
                f"flash_max_size={config.flash_max_size}"
            )

        # Reference cache: stores NeqsimFluid at standard conditions
        self._reference_cache: LRUCache = CacheService.create_cache(
            CacheName.REFERENCE_FLUID, max_size=config.reference_fluid_max_size
        )
        # Flash cache: stores FluidProperties for TP/PH flash results
        self._flash_cache: LRUCache = CacheService.create_cache(
            CacheName.FLUID_SERVICE_FLASH, max_size=config.flash_max_size
        )

    @classmethod
    def instance(cls) -> NeqSimFluidService:
        """Get the singleton instance of the service."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance and configuration. Useful for testing.

        Note: This does NOT remove caches from CacheService. Existing caches
        retain their size. For full reset including cache sizes (e.g., in tests),
        also clear the cache registry: CacheService._caches.clear()
        """
        cls._instance = None
        cls._cache_config = None

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

        Returns:
            Cache key tuple with structure:
            ("TP", composition_key, eos_model, rounded_pressure, rounded_temperature)

            This ensures unique cache entries for each distinct thermodynamic state.
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

        Returns:
            Cache key tuple with structure:
            ("PH", composition_key, eos_model, rounded_pressure, rounded_enthalpy)

            This ensures unique cache entries for each distinct thermodynamic state.
        """
        return (
            "PH",
            composition_key,
            eos_model,
            round(pressure, _PRESSURE_DECIMALS),
            round(target_enthalpy, _ENTHALPY_DECIMALS),
        )

    def _get_standard_density(self, fluid_model: FluidModel) -> float:
        """Get gas-phase density at standard conditions for volumetric rate conversions.

        Standard density is used to convert between mass rates (kg/h) and standard volumetric
        rates (Sm3/day). Since standard volumetric rates are defined for the gas phase only
        (Sm3 = Standard cubic meters of GAS), we must return gas-phase density even if liquid
        is present at standard conditions.

        Returns the density of the reference fluid at standard conditions (288.15 K, 1.01325 bara).
        Since the reference fluid is already at these conditions, no additional flash is required.

        For typical gas compositions, the fluid is entirely vapor at standard conditions.
        In rare cases where liquid is present, only the gas-phase density is returned,
        as standard density is defined for gases in volumetric rate conversions.

        Note: density is a @cached_property on NeqsimFluid, so repeated access
        should not trigger additional JVM calls.
        """
        ref = self._get_reference_fluid(fluid_model)

        # For gases, vapor_fraction should be ~1.0 at standard conditions
        if ref.vapor_fraction_molar >= ThermodynamicConstants.PURE_VAPOR_THRESHOLD:
            return ref.density

        # Rare case: liquid present at standard conditions - remove it
        gas_only = ref.clone_gas_phase()
        return gas_only.density

    def _extract_properties(self, neqsim_fluid: NeqsimFluid, fluid_model: FluidModel) -> FluidProperties:
        """Extract all properties from NeqsimFluid into pure dataclass.

        Args:
            neqsim_fluid: The NeqsimFluid to extract properties from
            fluid_model: The fluid model (composition + EoS)

        Note:
            We calculate molar_mass from FluidModel.composition rather than using
            neqsim_fluid.molar_mass because the latter requires JVM calls which
            are slow. FluidComposition.molar_mass_mixture computes this purely
            in Python from the component mole fractions.
        """
        return FluidProperties(
            temperature_kelvin=neqsim_fluid.temperature_kelvin,
            pressure_bara=neqsim_fluid.pressure_bara,
            density=neqsim_fluid.density,
            enthalpy_joule_per_kg=neqsim_fluid.enthalpy_joule_per_kg,
            z=neqsim_fluid.z,
            kappa=neqsim_fluid.kappa,
            vapor_fraction_molar=neqsim_fluid.vapor_fraction_molar,
            molar_mass=fluid_model.composition.molar_mass_mixture,
            standard_density=self._get_standard_density(fluid_model),
        )

    def flash_pt(
        self,
        fluid_model: FluidModel,
        pressure_bara: float,
        temperature_kelvin: float,
    ) -> FluidProperties:
        """TP flash returning fluid properties at specified conditions.

        Args:
            fluid_model: The fluid model (composition + EoS)
            pressure_bara: Target pressure in bara
            temperature_kelvin: Target temperature in Kelvin

        Returns:
            FluidProperties at the specified conditions.
        """
        composition = fluid_model.composition.normalized()
        composition_key = _make_composition_key(composition)
        cache_key = self._make_pt_cache_key(composition_key, fluid_model.eos_model, pressure_bara, temperature_kelvin)

        # Check cache first
        cached = self._flash_cache.get(cache_key)
        if cached is not None:
            return cached

        ref = self._get_reference_fluid(fluid_model)
        flashed = ref.set_new_pressure_and_temperature(
            new_pressure_bara=pressure_bara,
            new_temperature_kelvin=temperature_kelvin,
        )

        result = self._extract_properties(flashed, fluid_model)
        self._flash_cache.put(cache_key, result)
        return result

    def flash_ph(
        self,
        fluid_model: FluidModel,
        pressure_bara: float,
        target_enthalpy: float,
    ) -> FluidProperties:
        """PH flash to target pressure and enthalpy.

        Note: The target_enthalpy is reference-state dependent. NeqSim uses an arbitrary
        enthalpy reference state, so the caller must ensure that target_enthalpy was
        computed from enthalpy values obtained from the same EoS/fluid model session.
        Mixing enthalpy values from different thermodynamic packages or sessions may
        produce incorrect results.

        Args:
            fluid_model: The fluid model (composition + EoS)
            pressure_bara: Target pressure in bara
            target_enthalpy: Target specific enthalpy in J/kg (must be from same EoS session)

        Returns:
            FluidProperties at the specified conditions.
        """
        composition = fluid_model.composition.normalized()
        composition_key = _make_composition_key(composition)
        cache_key = self._make_ph_cache_key(composition_key, fluid_model.eos_model, pressure_bara, target_enthalpy)

        # Check cache first
        cached = self._flash_cache.get(cache_key)
        if cached is not None:
            return cached

        ref = self._get_reference_fluid(fluid_model)
        flashed = ref.set_new_pressure_and_enthalpy(
            new_pressure=pressure_bara,
            new_enthalpy_joule_per_kg=target_enthalpy,
        )

        result = self._extract_properties(flashed, fluid_model)
        self._flash_cache.put(cache_key, result)
        return result

    def remove_liquid(self, fluid: Fluid) -> Fluid:
        """Remove liquid phase from fluid, returning gas-phase only.

        Performs a TP flash at the fluid's current conditions and extracts only
        the gas phase. The returned Fluid will have updated composition reflecting
        the gas-phase composition.

        Args:
            fluid: The fluid to remove liquid from

        Returns:
            New Fluid with liquid removed (gas-phase only). Composition will be
            updated to reflect the gas-phase composition if liquid was present.
        """
        # If already all vapor, return as-is
        if fluid.vapor_fraction_molar >= ThermodynamicConstants.PURE_VAPOR_THRESHOLD:
            return fluid

        # Flash to current conditions to get NeqsimFluid, then extract gas phase
        ref = self._get_reference_fluid(fluid.fluid_model)
        flashed = ref.set_new_pressure_and_temperature(
            new_pressure_bara=fluid.pressure_bara,
            new_temperature_kelvin=fluid.temperature_kelvin,
        )

        # Extract gas phase only
        gas_only = flashed.clone_gas_phase()
        gas_composition = gas_only.composition

        # Create new Fluid with gas-phase composition
        new_fluid_model = FluidModel(composition=gas_composition, eos_model=fluid.fluid_model.eos_model)
        props = self._extract_properties(gas_only, new_fluid_model)
        return Fluid(fluid_model=new_fluid_model, properties=props)

    # === Factory Methods (implementing FluidService interface) ===

    def create_fluid(
        self,
        fluid_model: FluidModel,
        pressure_bara: float,
        temperature_kelvin: float,
    ) -> Fluid:
        """Create a Fluid at specified conditions via TP flash.

        Args:
            fluid_model: The fluid model (composition + EoS)
            pressure_bara: Target pressure in bara
            temperature_kelvin: Target temperature in Kelvin

        Returns:
            New Fluid instance at the specified conditions.
        """
        props = self.flash_pt(fluid_model, pressure_bara, temperature_kelvin)
        return Fluid(fluid_model=fluid_model, properties=props)

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
        return standard_rate_m3_per_day * standard_density / 24.0

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
        return mass_rate_kg_per_h * 24.0 / standard_density


def get_fluid_service_stats() -> dict[str, dict]:
    """Get cache statistics for the fluid service caches."""
    ref_cache = CacheService.get_cache(CacheName.REFERENCE_FLUID)
    flash_cache = CacheService.get_cache(CacheName.FLUID_SERVICE_FLASH)
    return {
        CacheName.REFERENCE_FLUID.value: ref_cache.get_stats() if ref_cache else {},
        CacheName.FLUID_SERVICE_FLASH.value: flash_cache.get_stats() if flash_cache else {},
    }
