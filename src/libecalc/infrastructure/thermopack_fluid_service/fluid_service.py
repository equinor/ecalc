"""ThermopackFluidService — drop-in replacement for NeqSimFluidService.

Uses thermopack (Fortran/ctypes) for flash calculations instead of NeqSim (Java/JVM).
"""

from __future__ import annotations

import logging
from typing import ClassVar

import numpy as np
from thermopack.cubic import cubic

from libecalc.domain.process.value_objects.fluid_stream.constants import ThermodynamicConstants
from libecalc.domain.process.value_objects.fluid_stream.fluid import Fluid
from libecalc.domain.process.value_objects.fluid_stream.fluid_model import EoSModel, FluidComposition, FluidModel
from libecalc.domain.process.value_objects.fluid_stream.fluid_properties import FluidProperties
from libecalc.domain.process.value_objects.fluid_stream.fluid_service import FluidService
from libecalc.domain.process.value_objects.fluid_stream.fluid_stream import FluidStream
from libecalc.infrastructure.cache_service import CacheConfig, CacheName, CacheService, LRUCache
from libecalc.infrastructure.thermopack_fluid_service.component_mapping import (
    ECALC_TO_THERMOPACK,
    composition_to_thermopack,
)

_logger = logging.getLogger(__name__)

R_GAS = ThermodynamicConstants.R_J_PER_MOL_K  # 8.31446261815324 J/(mol·K)

# Cache key rounding (same as NeqSimFluidService)
_PRESSURE_DECIMALS = 6
_TEMPERATURE_DECIMALS = 6
_ENTHALPY_DECIMALS = 6
_COMPOSITION_DECIMALS = 8

# Standard conditions
_STANDARD_TEMPERATURE_KELVIN = 288.15
_STANDARD_PRESSURE_BARA = 1.01325
_STANDARD_PRESSURE_PA = _STANDARD_PRESSURE_BARA * 1e5

# EoS mapping
_EOS_MAP: dict[EoSModel, str] = {
    EoSModel.SRK: "SRK",
    EoSModel.PR: "PR",
}


def _make_composition_key(composition: FluidComposition) -> tuple:
    """Create hashable cache key from composition with rounding for cache effectiveness."""
    return tuple((k, round(v, _COMPOSITION_DECIMALS)) for k, v in sorted(composition.model_dump().items()))


def _bara_to_pa(pressure_bara: float) -> float:
    return pressure_bara * 1e5


class _PhaseProperties:
    """Thermodynamic properties for a single phase.

    When volume_shift is enabled, thermopack's specific_volume returns the Peneloux-shifted
    volume. NeqSim applies the same shift for density but reports Z from the unshifted cubic
    root. We match that convention: density uses V_shifted, Z uses V_unshifted.
    """

    __slots__ = ("density", "z", "enthalpy_j_per_mol", "cp_j_per_mol_k", "kappa", "molar_volume")

    def __init__(
        self,
        eos: cubic,
        T: float,
        P_pa: float,
        z_phase: np.ndarray,
        phase_flag: int,
        molar_mass: float,
        volume_correction: float,
    ):
        (v_shifted,) = eos.specific_volume(T, P_pa, z_phase, phase_flag)
        v_unshifted = v_shifted + volume_correction
        h, cp = eos.enthalpy(T, P_pa, z_phase, phase_flag, dhdt=True)

        self.molar_volume = v_shifted  # m³/mol (shifted, for density)
        self.density = molar_mass / v_shifted  # kg/m³
        self.z = P_pa * v_unshifted / (R_GAS * T)  # compressibility (unshifted)
        self.enthalpy_j_per_mol = h  # J/mol
        self.cp_j_per_mol_k = cp  # J/(mol·K) — dH/dT at constant P
        self.kappa = cp / (cp - R_GAS)  # gamma2 = Cp/(Cp-R)


class ThermopackFluidService(FluidService):
    """Thermodynamic flash service backed by thermopack (Fortran/ctypes).

    Singleton with process-local caching. No JVM required.
    """

    _instance: ClassVar[ThermopackFluidService | None] = None
    _cache_config: ClassVar[CacheConfig | None] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def configure(cls, cache_config: CacheConfig) -> None:
        """Configure cache sizes before first use.

        Must be called BEFORE the first call to instance().

        Args:
            cache_config: Cache configuration with max sizes.
        """
        if cls._instance is not None:
            raise RuntimeError(
                "ThermopackFluidService.configure() must be called before the first "
                "instance() call. The singleton has already been created."
            )
        cls._cache_config = cache_config

    def __init__(self) -> None:
        if hasattr(self, "_initialized"):
            return
        self._initialized = True

        if self._cache_config is not None:
            config = self._cache_config
        else:
            config = CacheConfig.default()

        self._base_cache: LRUCache[tuple, tuple[cubic, list[str], np.ndarray, np.ndarray, float]] = (
            CacheService.create_cache(CacheName.FLUID_SERVICE_BASE, max_size=config.base_cache_max_size)
        )
        self._flash_cache: LRUCache[tuple, FluidProperties] = CacheService.create_cache(
            CacheName.FLUID_SERVICE_FLASH, max_size=config.flash_max_size
        )

        _logger.info(
            f"ThermopackFluidService initialized: "
            f"base_cache_max={config.base_cache_max_size}, "
            f"flash_cache_max={config.flash_max_size}"
        )

    @classmethod
    def instance(cls) -> ThermopackFluidService:
        """Get the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton. Useful for testing."""
        cls._instance = None
        cls._cache_config = None

    # ── Internal helpers ──────────────────────────────────────────────

    def _get_eos(self, fluid_model: FluidModel) -> tuple[cubic, list[str], np.ndarray, np.ndarray, float]:
        """Get or create a thermopack cubic instance for the given fluid model.

        Returns:
            Tuple of (eos_instance, ecalc_component_names, mole_fractions, ci_values, standard_density)
        """
        eos_model = fluid_model.eos_model
        if eos_model not in _EOS_MAP:
            raise NotImplementedError(
                f"EoS model '{eos_model.value}' is not supported by thermopack. "
                f"Supported models: {', '.join(m.value for m in _EOS_MAP)}"
            )

        composition = fluid_model.composition.normalized()
        comp_key = _make_composition_key(composition)
        cache_key = (comp_key, eos_model)

        cached = self._base_cache.get(cache_key)
        if cached is not None:
            return cached

        tp_eos_name = _EOS_MAP[eos_model]
        component_string, z, ecalc_names = composition_to_thermopack(composition)

        eos = cubic(component_string, tp_eos_name, volume_shift=True)

        # Pre-compute Peneloux volume correction: Σ(z_i * c_i)
        # Used to recover unshifted molar volume for Z computation (NeqSim convention).
        ci_values = np.array([eos.get_ci(i + 1)[0] for i in range(len(z))])

        # Pre-compute standard density (gas-phase at 288.15 K, 1.01325 bara)
        molar_mass = fluid_model.composition.molar_mass_mixture
        std_density = self._compute_standard_density(eos, z, ci_values, molar_mass)

        result = (eos, ecalc_names, z, ci_values, std_density)
        self._base_cache.put(cache_key, result)
        return result

    def _flash_cache_get(self, key: tuple) -> FluidProperties | None:
        return self._flash_cache.get(key)

    def _flash_cache_put(self, key: tuple, value: FluidProperties) -> None:
        self._flash_cache.put(key, value)

    def _compute_properties(
        self,
        eos: cubic,
        T_k: float,
        P_pa: float,
        z: np.ndarray,
        molar_mass: float,
        ci_values: np.ndarray,
    ) -> tuple[float, float, float, float, float, float]:
        """Run TP flash and compute bulk properties.

        Returns:
            (density, z_factor, kappa, enthalpy_j_per_kg, vapor_fraction, temperature_from_flash)
        """
        result = eos.two_phase_tpflash(T_k, P_pa, z)

        if result.phase == eos.TWOPH:
            betaV = result.betaV
            betaL = 1.0 - betaV

            vol_corr_vap = float(np.dot(result.y, ci_values))
            vol_corr_liq = float(np.dot(result.x, ci_values))

            vap = _PhaseProperties(eos, T_k, P_pa, result.y, eos.VAPPH, molar_mass, vol_corr_vap)
            liq = _PhaseProperties(eos, T_k, P_pa, result.x, eos.LIQPH, molar_mass, vol_corr_liq)

            # Bulk mixture molar volume (mole-fraction weighted, shifted for density)
            v_mix = betaV * vap.molar_volume + betaL * liq.molar_volume
            density = molar_mass / v_mix

            # Z from unshifted volumes (NeqSim convention)
            vol_corr_mix = betaV * vol_corr_vap + betaL * vol_corr_liq
            v_mix_unshifted = v_mix + vol_corr_mix
            z_factor = P_pa * v_mix_unshifted / (R_GAS * T_k)

            # Bulk enthalpy (molar average → mass)
            h_mix = betaV * vap.enthalpy_j_per_mol + betaL * liq.enthalpy_j_per_mol
            enthalpy_j_per_kg = h_mix / molar_mass

            # Bulk kappa
            cp_mix = betaV * vap.cp_j_per_mol_k + betaL * liq.cp_j_per_mol_k
            kappa = cp_mix / (cp_mix - R_GAS)

            return density, z_factor, kappa, enthalpy_j_per_kg, betaV, T_k

        else:
            # Single phase — determine phase flag
            phase_flag = eos.guess_phase(T_k, P_pa, z)
            vol_corr = float(np.dot(z, ci_values))
            props = _PhaseProperties(eos, T_k, P_pa, z, phase_flag, molar_mass, vol_corr)

            vapor_fraction = 1.0 if phase_flag == eos.VAPPH else 0.0

            return (
                props.density,
                props.z,
                props.kappa,
                props.enthalpy_j_per_mol / molar_mass,
                vapor_fraction,
                T_k,
            )

    @staticmethod
    def _compute_standard_density(eos: cubic, z: np.ndarray, ci_values: np.ndarray, molar_mass: float) -> float:
        """Compute gas-phase density at standard conditions (288.15 K, 1.01325 bara)."""
        result = eos.two_phase_tpflash(_STANDARD_TEMPERATURE_KELVIN, _STANDARD_PRESSURE_PA, z)

        if result.phase == eos.TWOPH and result.betaV > 0:
            vol_corr = float(np.dot(result.y, ci_values))
            vap = _PhaseProperties(
                eos,
                _STANDARD_TEMPERATURE_KELVIN,
                _STANDARD_PRESSURE_PA,
                result.y,
                eos.VAPPH,
                molar_mass,
                vol_corr,
            )
            return vap.density
        else:
            phase_flag = eos.guess_phase(_STANDARD_TEMPERATURE_KELVIN, _STANDARD_PRESSURE_PA, z)
            vol_corr = float(np.dot(z, ci_values))
            props = _PhaseProperties(
                eos,
                _STANDARD_TEMPERATURE_KELVIN,
                _STANDARD_PRESSURE_PA,
                z,
                phase_flag,
                molar_mass,
                vol_corr,
            )
            return props.density

    def _get_standard_density(self, fluid_model: FluidModel) -> float:
        """Get gas-phase density at standard conditions (288.15 K, 1.01325 bara).

        Pre-computed and cached alongside the EOS instance in the base cache.
        """
        _, _, _, _, std_density = self._get_eos(fluid_model)
        return std_density

    # ── FluidService interface ────────────────────────────────────────

    def flash_pt(
        self,
        fluid_model: FluidModel,
        pressure_bara: float,
        temperature_kelvin: float,
    ) -> FluidProperties:
        """TP flash returning fluid properties at specified conditions."""
        composition = fluid_model.composition.normalized()
        comp_key = _make_composition_key(composition)

        cache_key = (
            "TP",
            comp_key,
            fluid_model.eos_model,
            round(pressure_bara, _PRESSURE_DECIMALS),
            round(temperature_kelvin, _TEMPERATURE_DECIMALS),
        )
        cached = self._flash_cache_get(cache_key)
        if cached is not None:
            return cached

        eos, _, z, ci_values, _ = self._get_eos(fluid_model)
        molar_mass = fluid_model.composition.molar_mass_mixture
        P_pa = _bara_to_pa(pressure_bara)

        density, z_factor, kappa, enthalpy_j_per_kg, vf, _ = self._compute_properties(
            eos, temperature_kelvin, P_pa, z, molar_mass, ci_values
        )

        result = FluidProperties(
            temperature_kelvin=temperature_kelvin,
            pressure_bara=pressure_bara,
            density=density,
            enthalpy_joule_per_kg=enthalpy_j_per_kg,
            z=z_factor,
            kappa=kappa,
            vapor_fraction_molar=vf,
            molar_mass=molar_mass,
            standard_density=self._get_standard_density(fluid_model),
        )
        self._flash_cache_put(cache_key, result)
        return result

    def flash_ph(
        self,
        fluid_model: FluidModel,
        pressure_bara: float,
        target_enthalpy: float,
    ) -> FluidProperties:
        """PH flash to target pressure and enthalpy.

        target_enthalpy must be in J/kg and from the same thermopack session
        (reference-state dependent).
        """
        composition = fluid_model.composition.normalized()
        comp_key = _make_composition_key(composition)

        cache_key = (
            "PH",
            comp_key,
            fluid_model.eos_model,
            round(pressure_bara, _PRESSURE_DECIMALS),
            round(target_enthalpy, _ENTHALPY_DECIMALS),
        )
        cached = self._flash_cache_get(cache_key)
        if cached is not None:
            return cached

        eos, _, z, ci_values, _ = self._get_eos(fluid_model)
        molar_mass = fluid_model.composition.molar_mass_mixture
        P_pa = _bara_to_pa(pressure_bara)

        # Convert J/kg → J/mol for thermopack
        h_target_j_per_mol = target_enthalpy * molar_mass

        ph_result = eos.two_phase_phflash(P_pa, z, h_target_j_per_mol)
        T_k = ph_result.T

        # Now compute full properties at the resulting temperature
        density, z_factor, kappa, enthalpy_j_per_kg, vf, _ = self._compute_properties(
            eos, T_k, P_pa, z, molar_mass, ci_values
        )

        result = FluidProperties(
            temperature_kelvin=T_k,
            pressure_bara=pressure_bara,
            density=density,
            enthalpy_joule_per_kg=enthalpy_j_per_kg,
            z=z_factor,
            kappa=kappa,
            vapor_fraction_molar=vf,
            molar_mass=molar_mass,
            standard_density=self._get_standard_density(fluid_model),
        )
        self._flash_cache_put(cache_key, result)
        return result

    def remove_liquid(self, fluid: Fluid) -> Fluid:
        """Remove liquid phase, returning gas-phase only with updated composition."""
        if fluid.vapor_fraction_molar >= ThermodynamicConstants.PURE_VAPOR_THRESHOLD:
            return fluid

        eos, ecalc_names, z, _, _ = self._get_eos(fluid.fluid_model)
        P_pa = _bara_to_pa(fluid.pressure_bara)
        T_k = fluid.temperature_kelvin

        result = eos.two_phase_tpflash(T_k, P_pa, z)

        if result.phase != eos.TWOPH or result.betaV <= 0:
            return fluid

        # Build gas-phase FluidComposition from result.y
        gas_comp_dict: dict[str, float] = {}
        for i, name in enumerate(ecalc_names):
            gas_comp_dict[name] = float(result.y[i])

        # Fill missing components with 0
        for name in ECALC_TO_THERMOPACK:
            if name not in gas_comp_dict:
                gas_comp_dict[name] = 0.0

        gas_composition = FluidComposition(**gas_comp_dict)
        new_fluid_model = FluidModel(composition=gas_composition, eos_model=fluid.fluid_model.eos_model)

        props = self.flash_pt(new_fluid_model, fluid.pressure_bara, T_k)
        return Fluid(fluid_model=new_fluid_model, properties=props)

    def create_fluid(
        self,
        fluid_model: FluidModel,
        pressure_bara: float,
        temperature_kelvin: float,
    ) -> Fluid:
        """Create a Fluid at specified conditions via TP flash."""
        props = self.flash_pt(fluid_model, pressure_bara, temperature_kelvin)
        return Fluid(fluid_model=fluid_model, properties=props)

    def create_stream_from_standard_rate(
        self,
        fluid_model: FluidModel,
        pressure_bara: float,
        temperature_kelvin: float,
        standard_rate_m3_per_day: float,
    ) -> FluidStream:
        """Create a fluid stream from standard volumetric rate."""
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
        """Create a fluid stream from mass rate."""
        fluid = self.create_fluid(fluid_model, pressure_bara, temperature_kelvin)
        return FluidStream(fluid=fluid, mass_rate_kg_per_h=mass_rate_kg_per_h)

    def standard_rate_to_mass_rate(
        self,
        fluid_model: FluidModel,
        standard_rate_m3_per_day: float,
    ) -> float:
        """Convert standard volumetric rate [Sm3/day] to mass rate [kg/h]."""
        return standard_rate_m3_per_day * self._get_standard_density(fluid_model) / 24.0

    def mass_rate_to_standard_rate(
        self,
        fluid_model: FluidModel,
        mass_rate_kg_per_h: float,
    ) -> float:
        """Convert mass rate [kg/h] to standard volumetric rate [Sm3/day]."""
        return mass_rate_kg_per_h * 24.0 / self._get_standard_density(fluid_model)

    # ── Cache management ──────────────────────────────────────────────

    def clear_caches(self) -> None:
        """Clear all caches."""
        self._base_cache.clear()
        self._flash_cache.clear()

    def get_cache_stats(self) -> dict[str, dict]:
        """Get stats from all thermopack caches."""
        return {
            CacheName.FLUID_SERVICE_BASE: self._base_cache.get_stats(),
            CacheName.FLUID_SERVICE_FLASH: self._flash_cache.get_stats(),
        }
