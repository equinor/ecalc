from __future__ import annotations

from ecalc_neqsim_wrapper.thermo import NeqsimFluid
from libecalc.common.units import UnitConstants
from libecalc.domain.process.core.stream.conditions import ProcessConditions
from libecalc.domain.process.core.stream.fluid import Fluid, ThermodynamicEngine
from libecalc.domain.process.core.stream.thermo_constants import ThermodynamicConstants
from libecalc.domain.process.core.stream.thermo_utils import (
    calculate_molar_mass,
    calculate_z_factor_explicit_with_sour_gas_correction,
)


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

    def _create_neqsim_fluid(self, fluid: Fluid, *, pressure: float, temperature: float) -> NeqsimFluid:
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

    def get_density(self, fluid: Fluid, *, pressure: float, temperature: float) -> float:
        """
        Get density of the gas phase at given conditions.

        Returns:
            Density in kg/Am³
        """
        neqsim_fluid = self._create_neqsim_fluid(fluid, pressure=pressure, temperature=temperature)
        return neqsim_fluid.density

    def get_enthalpy(self, fluid: Fluid, *, pressure: float, temperature: float) -> float:
        """
        Get specific enthalpy at given conditions relative to reference conditions.

        Returns:
            Specific enthalpy in J/kg
        """
        neqsim_fluid = self._create_neqsim_fluid(fluid, pressure=pressure, temperature=temperature)
        return neqsim_fluid.enthalpy_joule_per_kg

    def get_z(self, fluid: Fluid, *, pressure: float, temperature: float) -> float:
        """
        Get compressibility factor (Z) at given conditions (gas phase)

        Returns:
            Z-factor (dimensionless)
        """
        neqsim_fluid = self._create_neqsim_fluid(fluid, pressure=pressure, temperature=temperature)
        return neqsim_fluid.z

    def get_kappa(self, fluid: Fluid, *, pressure: float, temperature: float) -> float:
        """
        Get heat capacity ratio (kappa) at given conditions.

        Returns:
            Kappa (isentropic exponent, dimensionless)
        """
        neqsim_fluid = self._create_neqsim_fluid(fluid, pressure=pressure, temperature=temperature)
        return neqsim_fluid.kappa

    def get_molar_mass(self, fluid: Fluid) -> float:
        """
        Get molar mass of the fluid.

        Returns:
            Molar mass in kg/mol
        """
        # Create at standard conditions, since molar mass is composition-dependent only
        standard_conditions = ProcessConditions.standard_conditions()
        neqsim_fluid = self._create_neqsim_fluid(
            fluid,
            pressure=standard_conditions.pressure_bara,
            temperature=standard_conditions.temperature_kelvin,
        )
        return neqsim_fluid.molar_mass

    def get_standard_density_gas_phase_after_flash(self, fluid: Fluid) -> float:
        """
        Get gas phase density at standard conditions after TP flash and liquid removal of potential liquid phase.

        Returns:
            Gas phase density in kg/Sm³
        """
        # Create fluid at standard conditions
        standard_conditions = ProcessConditions.standard_conditions()
        neqsim_fluid_at_standard_conditions = NeqsimFluid.create_thermo_system(
            composition=fluid.composition,
            temperature_kelvin=standard_conditions.temperature_kelvin,
            pressure_bara=standard_conditions.pressure_bara,
            eos_model=fluid.eos_model,
        )

        # TP flash is already performed during create_thermo_system
        # Remove liquid phase to ensure we have only gas phase
        liquid_removed_fluid = neqsim_fluid_at_standard_conditions.set_new_pressure_and_temperature(
            new_pressure_bara=standard_conditions.pressure_bara,
            new_temperature_kelvin=standard_conditions.temperature_kelvin,
            remove_liquid=True,
        )

        return liquid_removed_fluid.density

    def get_vapor_fraction_molar(self, fluid: Fluid, *, pressure: float, temperature: float) -> float:
        """
        Get molar gas fraction at given conditions.

        Returns:
            Gas fraction as a value between 0.0 and 1.0
        """
        neqsim_fluid = self._create_neqsim_fluid(fluid, pressure=pressure, temperature=temperature)
        return neqsim_fluid.vapor_fraction_molar


class ExplicitCorrelationThermodynamicAdapter(ThermodynamicEngine):
    """
    Simplified thermodynamic adapter using explicit correlations for some properties.

    This adapter provides fast, lightweight thermodynamic calculations without
    requiring iterative equation of state (EoS) solvers. It uses explicit
    correlations for key properties:

    - Compressibility (Z) factor: Based on pseudo-reduced properties
    - Heat capacity ratio (kappa): Based on temperature-dependent correlations
    - Enthalpy: Calculated from specific heat capacity with Z-factor correction
    - Density: Using real gas law with Z-factor
    - Properties requiring Flash: TODO: To be delegated to NeqSim adapter

    Note: This adapter sacrifices some accuracy for performance and simplicity.
    It's suitable for quick estimates and situations where computational
    efficiency is prioritized over rigorous thermodynamic accuracy.
    """

    R_J_PER_MOL_K = ThermodynamicConstants.R_J_PER_MOL_K  # J/(mol·K)

    def get_z(self, fluid: Fluid, *, pressure: float, temperature: float) -> float:
        """
        Calculate the compressibility factor (Z) using the linearized Z-factor correlation
        with CO2 content correction.

        Args:
            fluid: The fluid to calculate Z-factor for
            pressure: Pressure in bara
            temperature: Temperature in Kelvin

        Returns:
            Z-factor (dimensionless)
        """
        # Use the utility function with sour gas correction
        return calculate_z_factor_explicit_with_sour_gas_correction(fluid, pressure, temperature)

    def get_molar_mass(self, fluid: Fluid) -> float:
        """
        Calculate molar mass of the fluid based on composition.

        Returns:
            Molar mass in kg/mol
        """
        return calculate_molar_mass(fluid)

    def _calculate_cp(self, fluid: Fluid, temperature: float) -> float:
        """
        TODO: Implement correlation for Cp
        Calculate specific heat capacity at constant pressure.
        This is a simplified implementation using constant values per component.

        Returns:
            Cp in J/(mol·K)
        """
        # Get composition as a dictionary
        composition_dict = fluid.composition.model_dump()

        # Simple approximation values for components at moderate temperatures
        # These could be replaced with polynomial temperature-dependent coefficients
        cp_values = {
            "nitrogen": 29.0,
            "CO2": 37.0,
            "methane": 35.0,
            "ethane": 52.0,
            "propane": 74.0,
            "i_butane": 96.0,
            "n_butane": 98.0,
            "i_pentane": 120.0,
            "n_pentane": 121.0,
            "n_hexane": 142.0,
            "water": 33.6,
        }

        # Calculate weighted sum of heat capacities
        cp_sum = 0.0
        total_mole_fraction = 0.0

        for component, mole_fraction in composition_dict.items():
            if mole_fraction > 0 and component in cp_values:
                cp_sum += mole_fraction * cp_values[component]
                total_mole_fraction += mole_fraction

        # Normalize if total mole fraction is not 1.0
        if total_mole_fraction > 0:
            return cp_sum / total_mole_fraction
        else:
            # Default to methane if composition is empty (should not happen)
            return cp_values["methane"]

    def get_kappa(self, fluid: Fluid, *, pressure: float, temperature: float) -> float:
        """
        TODO: Create implementation accounting for real gas effects
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

    def get_density(self, fluid: Fluid, *, pressure: float, temperature: float) -> float:
        """
        Calculate density using real gas law with Z-factor correction.

        ρ = (P * Mw) / (Z * R * T)

        Returns:
            Density in kg/m³
        """
        # Get Z-factor and molar mass
        z = self.get_z(fluid, pressure=pressure, temperature=temperature)
        mw = self.get_molar_mass(fluid)

        # Convert pressure from bara to Pa
        pressure_pa = pressure * 1e5

        # Calculate density using real gas law
        # ρ = (P * MW) / (Z * R * T)
        density = (pressure_pa * mw) / (z * self.R_J_PER_MOL_K * temperature)

        return density

    def get_enthalpy(self, fluid: Fluid, *, pressure: float, temperature: float) -> float:
        """
        Calculate specific enthalpy at given conditions.

        Note: This is a temporary implementation that returns a dummy value.
        Proper implementation will be added later.

        Returns:
            Specific enthalpy in J/kg
        """
        return 1.0

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
        z = self.get_z(
            fluid, pressure=UnitConstants.STANDARD_PRESSURE_BARA, temperature=UnitConstants.STANDARD_TEMPERATURE_KELVIN
        )

        # Calculate density using ideal gas law
        # ρ = (P * MW) / (Z * R * T)
        density = (pressure_pa * mw) / (z * self.R_J_PER_MOL_K * temperature_k)

        return density

    def get_vapor_fraction_molar(self, fluid: Fluid, *, pressure: float, temperature: float) -> float:
        """
        Get molar gas fraction at given conditions.

        For the explicit correlation adapter, we delegate to NeqSim for vapor fraction calculation
        as it requires a flash calculation.
        TODO: Delegate to NeqSim adapter

        Returns:
            Gas fraction as a value between 0.0 and 1.0
        """
        # Default to all gas for typical conditions
        return 1.0
