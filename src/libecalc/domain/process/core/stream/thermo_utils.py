"""
Utilities for thermodynamic calculations in the process domain.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from libecalc.domain.process.core.stream.fluid import Fluid


class ThermodynamicConstants:
    """Constants used in thermodynamic calculations."""

    # Gas constant in various units
    R_J_PER_MOL_K = 8.31446261815324  # J/(mol·K)

    # Critical properties for common components (Tc in K, Pc in bara)
    CRITICAL_PROPERTIES = {
        "nitrogen": {"Tc": 126.2, "Pc": 33.9, "omega": 0.04},
        "CO2": {"Tc": 304.2, "Pc": 73.8, "omega": 0.239},
        "methane": {"Tc": 190.6, "Pc": 46.0, "omega": 0.011},
        "ethane": {"Tc": 305.4, "Pc": 48.8, "omega": 0.099},
        "propane": {"Tc": 369.8, "Pc": 42.5, "omega": 0.152},
        "i_butane": {"Tc": 408.1, "Pc": 36.5, "omega": 0.186},
        "n_butane": {"Tc": 425.2, "Pc": 38.0, "omega": 0.2},
        "i_pentane": {"Tc": 460.4, "Pc": 33.8, "omega": 0.229},
        "n_pentane": {"Tc": 469.7, "Pc": 33.7, "omega": 0.251},
        "n_hexane": {"Tc": 507.5, "Pc": 30.1, "omega": 0.299},
        "water": {"Tc": 647.1, "Pc": 220.6, "omega": 0.344},
    }

    # Specific heat capacity coefficients (Cp = a + b*T + c*T^2 + d*T^3) [J/(mol·K)]
    CP_COEFFICIENTS = {
        "nitrogen": {"a": 28.98, "b": 1.853e-3, "c": -9.647e-6, "d": 16.64e-9},
        "CO2": {"a": 22.26, "b": 5.981e-2, "c": -3.501e-5, "d": 7.469e-9},
        "methane": {"a": 19.25, "b": 5.213e-2, "c": 1.197e-5, "d": -1.132e-8},
        "ethane": {"a": 5.409, "b": 1.781e-1, "c": -6.938e-5, "d": 8.713e-9},
        "propane": {"a": 5.616, "b": 2.300e-1, "c": -8.824e-5, "d": 1.097e-8},
        "i_butane": {"a": 4.872, "b": 3.063e-1, "c": -1.571e-4, "d": 3.196e-8},
        "n_butane": {"a": 9.487, "b": 3.313e-1, "c": -1.108e-4, "d": -2.822e-9},
        "i_pentane": {"a": 6.774, "b": 4.445e-1, "c": -2.300e-4, "d": 4.658e-8},
        "n_pentane": {"a": 6.771, "b": 4.541e-1, "c": -2.264e-4, "d": 4.403e-8},
        "n_hexane": {"a": 6.938, "b": 5.548e-1, "c": -2.830e-4, "d": 5.723e-8},
        "water": {"a": 32.24, "b": 1.924e-3, "c": 1.055e-5, "d": -3.596e-9},
    }

    # Molecular weights [kg/mol]
    MOL_WEIGHTS = {
        "water": 0.01801534,
        "nitrogen": 0.02801340,
        "CO2": 0.04400995,
        "methane": 0.01604246,
        "ethane": 0.03006904,
        "propane": 0.04409562,
        "i_butane": 0.05812220,
        "n_butane": 0.05812220,
        "i_pentane": 0.07214878,
        "n_pentane": 0.07214878,
        "n_hexane": 0.08617536,
    }


def calculate_pseudo_critical_properties(fluid: "Fluid") -> tuple[float, float, float]:
    """
    Calculate pseudo-critical properties for a mixture.

    Args:
        fluid: The fluid object containing composition information

    Returns:
        Tuple of (Tc, Pc, omega) where:
        - Tc: Critical temperature in K
        - Pc: Critical pressure in bara
        - omega: Acentric factor (dimensionless)
    """
    # Get composition as a dictionary
    composition_dict = fluid.composition.model_dump()

    # Initialize weighted sums
    tc_sum = 0.0
    pc_sum = 0.0
    omega_sum = 0.0
    total_mole_fraction = 0.0

    # Calculate weighted sums
    for component, mole_fraction in composition_dict.items():
        if mole_fraction > 0 and component in ThermodynamicConstants.CRITICAL_PROPERTIES:
            tc_sum += mole_fraction * ThermodynamicConstants.CRITICAL_PROPERTIES[component]["Tc"]
            pc_sum += mole_fraction * ThermodynamicConstants.CRITICAL_PROPERTIES[component]["Pc"]
            omega_sum += mole_fraction * ThermodynamicConstants.CRITICAL_PROPERTIES[component]["omega"]
            total_mole_fraction += mole_fraction

    # Normalize if total mole fraction is not 1.0
    if total_mole_fraction > 0:
        tc_pseudo = tc_sum / total_mole_fraction
        pc_pseudo = pc_sum / total_mole_fraction
        omega_pseudo = omega_sum / total_mole_fraction
    else:
        # Default values for empty composition (should not happen)
        tc_pseudo = 190.6  # Methane Tc
        pc_pseudo = 46.0  # Methane Pc
        omega_pseudo = 0.011  # Methane omega

    return tc_pseudo, pc_pseudo, omega_pseudo
