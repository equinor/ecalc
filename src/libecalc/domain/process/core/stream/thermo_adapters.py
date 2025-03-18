from __future__ import annotations

from ecalc_neqsim_wrapper.thermo import NeqsimFluid
from libecalc.domain.process.core.stream.conditions import ProcessConditions
from libecalc.domain.process.core.stream.fluid import Fluid, ThermodynamicEngine


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
