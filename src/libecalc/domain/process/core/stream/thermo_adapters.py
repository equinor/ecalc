from __future__ import annotations

import math
from typing import TYPE_CHECKING

from ecalc_neqsim_wrapper.thermo import NeqsimFluid
from libecalc.common.logger import logger
from libecalc.common.units import UnitConstants
from libecalc.domain.process.core.stream.fluid import ThermodynamicEngine
from libecalc.domain.process.core.stream.thermo_utils import (
    ThermodynamicConstants,
    calculate_pseudo_critical_properties,
)

# Only import Fluid for type checking to avoid circular import
if TYPE_CHECKING:
    from libecalc.domain.process.core.stream.fluid import Fluid


class NeqSimThermodynamicAdapter(ThermodynamicEngine):
    """
    Adapter for NeqSim thermodynamic calculations.

    This adapter translates between our domain model and NeqSim, using the ecalc_neqsim_wrapper
    to interface with the NeqSim Java service.

    Units are standardized as follows:
    - Pressure: bara
    - Temperature: Kelvin
    - Density: kg/m³
    - Enthalpy: kJ/kg
    - Molar mass: kg/mol
    """

    def _create_neqsim_fluid(self, fluid: Fluid, pressure: float, temperature: float) -> NeqsimFluid:
        """
        Create a NeqSim fluid from our domain model.

        Args:
            fluid: Our domain fluid model
            pressure: Pressure in bara
            temperature: Temperature in Kelvin

        Returns:
            NeqSim fluid object
        """
        return NeqsimFluid.create_thermo_system(
            composition=fluid.composition,
            temperature_kelvin=temperature,
            pressure_bara=pressure,
            eos_model=fluid.eos_model,
        )

    def get_density(self, fluid: Fluid, pressure: float, temperature: float) -> float:
        """
        Get density of the gas phase at given conditions.

        Returns:
            Density in kg/Am³
        """
        neqsim_fluid = self._create_neqsim_fluid(fluid, pressure, temperature)
        return neqsim_fluid.density

    def get_enthalpy(self, fluid: Fluid, pressure: float, temperature: float) -> float:
        """
        Get specific enthalpy at given conditions relative to reference conditions.

        Returns:
            Specific enthalpy in J/kg
        """
        neqsim_fluid = self._create_neqsim_fluid(fluid, pressure, temperature)
        return neqsim_fluid.enthalpy_joule_per_kg

    def get_z(self, fluid: Fluid, pressure: float, temperature: float) -> float:
        """
        Get compressibility factor (Z) at given conditions (gas phase)

        Returns:
            Z-factor (dimensionless)
        """
        neqsim_fluid = self._create_neqsim_fluid(fluid, pressure, temperature)
        return neqsim_fluid.z

    def get_kappa(self, fluid: Fluid, pressure: float, temperature: float) -> float:
        """
        Get heat capacity ratio (kappa) at given conditions.

        Returns:
            Kappa (isentropic exponent, dimensionless)
        """
        neqsim_fluid = self._create_neqsim_fluid(fluid, pressure, temperature)
        return neqsim_fluid.kappa

    def get_molar_mass(self, fluid: Fluid) -> float:
        """
        Get molar mass of the fluid.

        Returns:
            Molar mass in kg/mol
        """
        # Create at standard conditions, since molar mass is composition-dependent only
        neqsim_fluid = self._create_neqsim_fluid(
            fluid, pressure=UnitConstants.STANDARD_PRESSURE_BARA, temperature=UnitConstants.STANDARD_TEMPERATURE_KELVIN
        )
        return neqsim_fluid.molar_mass

    def get_standard_density_gas_phase_after_flash(self, fluid: Fluid) -> float:
        """
        Get gas phase density at standard conditions after TP flash and liquid removal of potential liquid phase.

        Standard conditions are defined in UnitConstants.

        Returns:
            Gas phase density in kg/Sm³
        """
        # Create fluid at standard conditions
        neqsim_fluid_at_standard_conditions = NeqsimFluid.create_thermo_system(
            composition=fluid.composition,
            temperature_kelvin=UnitConstants.STANDARD_TEMPERATURE_KELVIN,
            pressure_bara=UnitConstants.STANDARD_PRESSURE_BARA,
            eos_model=fluid.eos_model,
        )

        # TP flash is already performed during create_thermo_system
        # Remove liquid phase to ensure we have only gas phase
        liquid_removed_fluid = neqsim_fluid_at_standard_conditions.set_new_pressure_and_temperature(
            new_pressure_bara=UnitConstants.STANDARD_PRESSURE_BARA,
            new_temperature_kelvin=UnitConstants.STANDARD_TEMPERATURE_KELVIN,
            remove_liquid=True,
        )

        return liquid_removed_fluid.density

    def get_phase_fractions(self, fluid: Fluid, pressure: float, temperature: float) -> dict[str, float]:
        """
        Get phase distribution (gas/liquid fractions) at given conditions.

        Returns:
            Dictionary with phase fractions, e.g. {"gas": 0.8, "oil": 0.2}
        """
        neqsim_fluid = self._create_neqsim_fluid(fluid, pressure, temperature)
        return neqsim_fluid.phase_fractions


class ExplicitCorrelationThermodynamicAdapter(ThermodynamicEngine):
    """
    Simplified thermodynamic adapter using explicit correlations.

    This adapter provides fast, lightweight thermodynamic calculations without
    requiring iterative equation of state (EoS) solvers. It uses explicit
    correlations for key properties:

    - Compressibility (Z) factor: Based on pseudo-reduced properties
    - Heat capacity ratio (kappa): Based on temperature-dependent correlations
    - Enthalpy: Calculated from specific heat capacity with Z-factor correction
    - Density: Using real gas law with Z-factor

    Note: This adapter sacrifices some accuracy for performance and simplicity.
    It's suitable for quick estimates and situations where computational
    efficiency is prioritized over rigorous thermodynamic accuracy.
    """

    # Gas constant in various units
    R_J_PER_MOL_K = ThermodynamicConstants.R_J_PER_MOL_K  # J/(mol·K)

    def get_z(self, fluid: Fluid, pressure: float, temperature: float) -> float:
        """
        Calculate the compressibility factor (Z) using the linearized Z-factor correlation
        from "New explicit correlation for the compressibility factor of natural gas: linearized z-factor isotherms".

        Args:
            fluid: The fluid to calculate Z-factor for
            pressure: Pressure in bara
            temperature: Temperature in Kelvin

        Returns:
            Z-factor (dimensionless)
        """
        # Calculate pseudo-critical properties
        tc_mix, pc_mix, _ = calculate_pseudo_critical_properties(fluid)

        # Calculate pseudo-reduced properties
        t_pr = temperature / tc_mix if tc_mix > 0 else 1.0
        p_pr = pressure / pc_mix if pc_mix > 0 else 0.0

        # At very low pressures, gas is nearly ideal
        if p_pr < 0.2:
            return 1.0

        # At very high pressures or temperatures, use a simpler correlation
        # to avoid failed calculations and print a warning
        if p_pr > 15.0 or t_pr > 3.0:
            logger.warning(f"Using fallback correlation for Z-factor at high pressure Psr={p_pr} and Tsr={t_pr}")
            return 0.7 + 0.3 * t_pr / p_pr

        # Get CO2 and N2 fractions for correction
        composition_dict = fluid.composition.model_dump()
        co2_fraction = composition_dict.get("CO2", 0.0)
        n2_fraction = composition_dict.get("nitrogen", 0.0)

        try:
            # Constants from the paper
            a = [
                0.0,  # a_0 (not used, for indexing clarity)
                0.317842,  # a_1
                0.382216,  # a_2
                -7.768354,  # a_3
                14.290531,  # a_4
                0.000002,  # a_5
                -0.004693,  # a_6
                0.096254,  # a_7
                0.166720,  # a_8
                0.966910,  # a_9
                0.063069,  # a_10
                -1.966847,  # a_11
                21.0581,  # a_12
                -27.0246,  # a_13
                16.23,  # a_14
                207.783,  # a_15
                -488.161,  # a_16
                176.29,  # a_17
                1.88453,  # a_18
                3.05921,  # a_19
            ]

            # Inverse of reduced temperature
            t = 1.0 / t_pr

            # Calculate group parameters as per the paper
            A = a[1] * t * math.exp(a[2] * (1 - t) ** 2) * p_pr
            B = a[3] * t + a[4] * t**2 + a[5] * t**6 * p_pr**6
            C = a[9] + a[8] * t * p_pr + a[7] * t**2 * p_pr**2 + a[6] * t**3 * p_pr**3
            D = a[10] * t * math.exp(a[11] * (1 - t) ** 2)
            E = a[12] * t + a[13] * t**2 + a[14] * t**3
            F = a[15] * t + a[16] * t**2 + a[17] * t**3
            G = a[18] + a[19] * t

            # Calculate y using equation 15
            denominator = (1 + A**2) / C - (A**2 * B) / (C**3)

            # Check if denominator is valid (not zero, not too small)
            if abs(denominator) < 1e-10:
                # Fallback to a simple correlation if calculation fails
                logger.warning(
                    f"Using fallback correlation for Z-factor at pressure Psr={p_pr} and temperature Tsr={t_pr}"
                )
                z = 1.0 - (0.3 * p_pr / t_pr)
            else:
                y = (D * p_pr) / denominator

                # Calculate z using equation 14
                if abs(y - 1.0) < 1e-10:  # Avoid division by zero
                    logger.warning(
                        f"Using fallback correlation for Z-factor at pressure Psr={p_pr} and temperature Tsr={t_pr}"
                    )
                    z = 1.0
                else:
                    numerator = D * p_pr * (1 + y + y**2 - y**3)
                    denominator = (D * p_pr + E * y**2 - F * y**G) * (1 - y) ** 3

                    # Check if denominator is valid
                    if abs(denominator) < 1e-10:
                        z = 1.0 - (0.3 * p_pr / t_pr)  # Fallback correlation
                    else:
                        z = numerator / denominator

                        # Check if result is a real, finite number
                        if not (isinstance(z, int | float) and math.isfinite(z)):
                            z = 1.0 - (0.3 * p_pr / t_pr)  # Fallback correlation

        except (ValueError, ZeroDivisionError, OverflowError):
            # Fallback to a simple correlation if calculation fails
            z = 1.0 - (0.3 * p_pr / t_pr)

        # Empirical correction for CO2 and N2
        z_correction = 1.0 - 0.15 * co2_fraction - 0.08 * n2_fraction
        z *= z_correction

        # Ensure Z is in physically reasonable range
        z = max(0.3, min(1.5, z))

        return z

    def get_molar_mass(self, fluid: Fluid) -> float:
        """
        Calculate molar mass of the fluid based on composition.

        Returns:
            Molar mass in kg/mol
        """
        # Get composition as a dictionary
        composition_dict = fluid.composition.model_dump()

        # Calculate weighted sum of molecular weights
        mw_sum = 0.0
        total_mole_fraction = 0.0

        for component, mole_fraction in composition_dict.items():
            if mole_fraction > 0 and component in ThermodynamicConstants.MOL_WEIGHTS:
                mw_sum += mole_fraction * ThermodynamicConstants.MOL_WEIGHTS[component]
                total_mole_fraction += mole_fraction

        # Normalize if total mole fraction is not 1.0
        if total_mole_fraction > 0:
            return mw_sum / total_mole_fraction
        else:
            # Default to methane if composition is empty (should not happen)
            return ThermodynamicConstants.MOL_WEIGHTS["methane"]

    def _calculate_cp(self, fluid: Fluid, temperature: float) -> float:
        """
        Calculate specific heat capacity at constant pressure.

        Returns:
            Cp in J/(mol·K)
        """
        # Get composition as a dictionary
        composition_dict = fluid.composition.model_dump()

        # Calculate weighted sum of heat capacities
        cp_sum = 0.0
        total_mole_fraction = 0.0

        for component, mole_fraction in composition_dict.items():
            if mole_fraction > 0 and component in ThermodynamicConstants.CP_COEFFICIENTS:
                # Get coefficients
                coef = ThermodynamicConstants.CP_COEFFICIENTS[component]
                # Calculate Cp using polynomial: a + b*T + c*T^2 + d*T^3
                cp = coef["a"] + coef["b"] * temperature + coef["c"] * temperature**2 + coef["d"] * temperature**3
                cp_sum += mole_fraction * cp
                total_mole_fraction += mole_fraction

        # Normalize if total mole fraction is not 1.0
        if total_mole_fraction > 0:
            return cp_sum / total_mole_fraction
        else:
            # Default to methane if composition is empty (should not happen)
            coef = ThermodynamicConstants.CP_COEFFICIENTS["methane"]
            return coef["a"] + coef["b"] * temperature + coef["c"] * temperature**2 + coef["d"] * temperature**3

    def get_kappa(self, fluid: Fluid, pressure: float, temperature: float) -> float:
        """
        Calculate heat capacity ratio (Cp/Cv) for the given fluid.

        Returns:
            Heat capacity ratio (dimensionless)
        """
        # Calculate Cp in J/(mol·K)
        cp_j_per_mol_k = self._calculate_cp(fluid, temperature)

        # Calculate Cv = Cp - R
        cv_j_per_mol_k = cp_j_per_mol_k - self.R_J_PER_MOL_K

        # Calculate kappa (Cp/Cv)
        kappa = cp_j_per_mol_k / cv_j_per_mol_k

        # Ensure kappa is physically reasonable
        return max(1.0, min(kappa, 2.0))

    def get_density(self, fluid: Fluid, pressure: float, temperature: float) -> float:
        """
        Calculate density using real gas law with Z-factor correction.

        ρ = (P * MW) / (Z * R * T)

        Returns:
            Density in kg/m³
        """
        # Get Z-factor and molar mass
        z = self.get_z(fluid, pressure, temperature)
        mw = self.get_molar_mass(fluid)

        # Convert pressure from bara to Pa
        pressure_pa = pressure * 1e5

        # Calculate density using real gas law
        # ρ = (P * MW) / (Z * R * T)
        density = (pressure_pa * mw) / (z * self.R_J_PER_MOL_K * temperature)

        return density

    def get_enthalpy(self, fluid: Fluid, pressure: float, temperature: float) -> float:
        """
        Calculate specific enthalpy at given conditions.

        This uses a simplified approach based on ideal gas heat capacity
        with a correction for non-ideal behavior using the Z-factor.

        Returns:
            Specific enthalpy in kJ/kg
        """
        # Get molar mass and Z-factor
        mw = self.get_molar_mass(fluid)
        z = self.get_z(fluid, pressure, temperature)

        # Calculate specific heat capacity in J/(mol·K)
        cp_mol = self._calculate_cp(fluid, temperature)

        # Convert to mass basis: J/(mol·K) -> J/(kg·K)
        cp_mass = cp_mol / mw

        # Calculate enthalpy change from reference state (298.15 K, 1 bara)
        # H - H_ref = Cp * (T - T_ref) + correction for non-ideal behavior
        delta_t = temperature - 298.15

        # Simplified correction for non-ideal behavior
        # The (z-1) term accounts for the deviation from ideal gas
        non_ideal_correction = self.R_J_PER_MOL_K * temperature * (z - 1) / mw

        # Calculate enthalpy in J/kg
        enthalpy_j_per_kg = cp_mass * delta_t + non_ideal_correction

        # Convert to kJ/kg
        enthalpy_kj_per_kg = enthalpy_j_per_kg / 1000.0

        return enthalpy_kj_per_kg

    def get_standard_density_gas_phase_after_flash(self, fluid: Fluid) -> float:
        """
        Get gas phase density at standard conditions.

        For the explicit correlation adapter, we calculate the density at standard conditions
        using the ideal gas law (Z=1) which is a good approximation at standard conditions.

        Standard conditions are defined in UnitConstants.

        Returns:
            Gas phase density in kg/Sm³
        """
        # Get molar mass
        mw = self.get_molar_mass(fluid)

        # Standard conditions
        pressure_pa = UnitConstants.STANDARD_PRESSURE_BARA * 1e5
        temperature_k = UnitConstants.STANDARD_TEMPERATURE_KELVIN

        # At standard conditions, Z is very close to 1.0 for most natural gases
        # Using Z=1.0 (ideal gas) for standard density calculation
        z = 1.0

        # Calculate density using ideal gas law
        # ρ = (P * MW) / (Z * R * T)
        density = (pressure_pa * mw) / (z * self.R_J_PER_MOL_K * temperature_k)

        return density

    def get_phase_fractions(self, fluid: Fluid, pressure: float, temperature: float) -> dict[str, float]:
        """
        Get phase distribution at given conditions.

        For the explicit correlation adapter, we use a simplified approach:
        - If T > Tc_pseudo, assume 100% gas
        - If T < Tc_pseudo, use a simple correlation based on reduced properties

        Returns:
            Dictionary with phase fractions, e.g. {"gas": 1.0, "oil": 0.0}
        """
        # Get pseudo-critical properties
        tc_pseudo, pc_pseudo, _ = calculate_pseudo_critical_properties(fluid)

        # Calculate reduced properties
        tr = temperature / tc_pseudo
        pr = pressure / pc_pseudo

        # Simplified phase prediction
        if tr > 1.0:
            # Above critical temperature, always gas
            return {"gas": 1.0, "oil": 0.0}
        elif pr > 1.0 and tr < 0.8:
            # High pressure, low temperature - likely liquid
            return {"gas": 0.0, "oil": 1.0}
        elif pr < 0.5:
            # Low pressure - likely gas
            return {"gas": 1.0, "oil": 0.0}
        else:
            # Transition region - simplified correlation
            gas_fraction = min(1.0, max(0.0, tr * (1.0 - 0.5 * pr)))
            return {"gas": gas_fraction, "oil": 1.0 - gas_fraction}
