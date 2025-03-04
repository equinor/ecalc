from __future__ import annotations

from typing import TYPE_CHECKING

from ecalc_neqsim_wrapper.thermo import NeqsimFluid
from libecalc.common.units import UnitConstants
from libecalc.domain.process.core.stream.fluid import ThermodynamicEngine
from libecalc.domain.process.core.stream.thermo_utils import (
    ThermodynamicConstants,
    calculate_pseudo_critical_properties,
    calculate_z_factor,
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

    def get_gas_fraction_molar(self, fluid: Fluid, pressure: float, temperature: float) -> float:
        """
        Get molar gas fraction at given conditions.

        Returns:
            Gas fraction as a value between 0.0 and 1.0
        """
        neqsim_fluid = self._create_neqsim_fluid(fluid, pressure, temperature)
        return neqsim_fluid.gas_fraction_molar


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

    R_J_PER_MOL_K = ThermodynamicConstants.R_J_PER_MOL_K  # J/(mol·K)

    def get_z(self, fluid: Fluid, pressure: float, temperature: float) -> float:
        """
        Calculate the compressibility factor (Z) using the linearized Z-factor correlation

        Args:
            fluid: The fluid to calculate Z-factor for
            pressure: Pressure in bara
            temperature: Temperature in Kelvin

        Returns:
            Z-factor (dimensionless)
        """
        # Calculate pseudo-critical properties
        tc_mix, pc_mix, _ = calculate_pseudo_critical_properties(fluid)

        # Get CO2 fraction for Wichert and Aziz correction
        composition_dict = fluid.composition.model_dump()
        co2_fraction = composition_dict.get("CO2", 0.0)

        # Apply Wichert and Aziz correction for acid gases
        # Setting correction limit CO2 fraction low due to slightly better results, but most important if CO2 content is significant (> 5%)
        if co2_fraction > 0.005:
            # Calculate correction parameters
            A = co2_fraction  # Sum of acid gas mole fractions (only CO2 in this case)
            B = 0.0  # No H2S in the composition

            # Calculate correction factor (epsilon)
            epsilon = 120 * (A**0.9 - A**1.6) + 15 * (B**0.5 - B**4)

            # Apply correction to pseudo-critical properties
            tc_mix_corrected = tc_mix - epsilon

            # When B=0, the pressure correction simplifies to:
            pc_mix_corrected = pc_mix * tc_mix_corrected / tc_mix

            # Use corrected values
            tc_mix = tc_mix_corrected
            pc_mix = pc_mix_corrected

        # Calculate pseudo-reduced properties
        t_pr = temperature / tc_mix if tc_mix > 0 else 1.0
        p_pr = pressure / pc_mix if pc_mix > 0 else 0.0

        # Calculate Z-factor using the utility function
        z = calculate_z_factor(t_pr, p_pr)

        # May use a correction for N2, e.g. stewart-Burkhardt-Voo Correction
        # Note some correction should be used to correct z factor calculated without nitrogen.
        # Not using any correction for N2 since results are not any better than without it.
        # n2_fraction = composition_dict.get("nitrogen", 0.0)
        # z = z + (0.01 * n2_fraction)

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
        Get gas phase density at standard conditions after TP flash and liquid removal
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
        # May use Z=1.0 (ideal gas) for standard density calculation
        z = self.get_z(fluid, UnitConstants.STANDARD_PRESSURE_BARA, UnitConstants.STANDARD_TEMPERATURE_KELVIN)

        # Calculate density using ideal gas law
        # ρ = (P * MW) / (Z * R * T)
        density = (pressure_pa * mw) / (z * self.R_J_PER_MOL_K * temperature_k)

        return density

    def get_gas_fraction_molar(self, fluid: Fluid, pressure: float, temperature: float) -> float:
        """
        Cummy return 1 since phase vapor liq equilibrium are not available in the explicit correlation adapter yet
        Returns:
            Gas fraction as a value between 0.0 and 1.0
        """

        return 1
