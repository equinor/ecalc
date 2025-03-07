"""
Utilities for thermodynamic calculations in the process domain.
"""

import math
from typing import TYPE_CHECKING

from libecalc.common.logger import logger

if TYPE_CHECKING:
    from libecalc.domain.process.core.stream.fluid import Fluid


class ThermodynamicConstants:
    """Constants used in thermodynamic calculations."""

    # Gas constant in various units
    R_J_PER_MOL_K = 8.31446261815324  # J/(mol·K)

    # Critical properties for common components (Tc in K, Pc in bara)
    CRITICAL_PROPERTIES = {
        "nitrogen": {"Tc": 126.2, "Pc": 33.9, "omega": 0.039},
        "CO2": {"Tc": 304.1, "Pc": 73.8, "omega": 0.239},
        "methane": {"Tc": 190.4, "Pc": 46.0, "omega": 0.011},
        "ethane": {"Tc": 305.4, "Pc": 48.8, "omega": 0.099},
        "propane": {"Tc": 369.8, "Pc": 42.5, "omega": 0.153},
        "i_butane": {"Tc": 408.2, "Pc": 36.5, "omega": 0.183},
        "n_butane": {"Tc": 425.2, "Pc": 38.0, "omega": 0.199},
        "i_pentane": {"Tc": 460.4, "Pc": 33.9, "omega": 0.227},
        "n_pentane": {"Tc": 469.7, "Pc": 33.7, "omega": 0.251},
        "n_hexane": {"Tc": 507.5, "Pc": 30.1, "omega": 0.299},
        "water": {"Tc": 647.3, "Pc": 221.2, "omega": 0.344},
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
    Calculate pseudo-critical properties for a fluid mixture.

    Args:
        fluid: The fluid to calculate properties for

    Returns:
        Tuple of (Tc_pseudo, Pc_pseudo, omega_pseudo)
    """
    composition_dict = fluid.composition.model_dump()

    # Initialize sums
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
        logger.warning(
            "Empty composition provided for pseudo-critical properties calculation - using default values for methane"
        )
        tc_pseudo = 190.6  # Methane Tc
        pc_pseudo = 46.0  # Methane Pc
        omega_pseudo = 0.011  # Methane omega

    return tc_pseudo, pc_pseudo, omega_pseudo


def calculate_z_factor_explicit(t_pr: float, p_pr: float) -> float:
    """
    Calculate the compressibility factor (Z) using the linearized Z-factor correlation
    source:
    https://doi.org/10.1007/s13202-015-0209-3
    (Kareem et al, 2016)

    Args:
        t_pr: Reduced temperature (T/Tc)
        p_pr: Reduced pressure (P/Pc)

    Returns:
        Z-factor (dimensionless)
    """
    # At very low pressures, gas is nearly ideal
    if p_pr < 0.01:
        return 1.0

    # Check if we're outside the validity range of the correlation
    # The correlation is valid for: 1.15 < Tpr < 3.0 and 0.2 < Ppr < 15.0

    if t_pr < 1.15 or t_pr > 3.0 or p_pr > 15.0 or p_pr < 0.2:
        logger.warning(
            f"Correlation for Z is outside validity range (1.15 < Tpr < 3.0, 0.2 < Ppr < 15.0). "
            f"Have P_pr={p_pr:.2f} and T_pr={t_pr:.2f}"
        )

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
            logger.warning(f"Using fallback correlation for Z-factor at pressure Psr={p_pr} and temperature Tsr={t_pr}")
            # print(f"Using fallback correlation for Z-factor at pressure Psr={p_pr} and temperature Tsr={t_pr}")
            z = 1.0 - (0.3 * p_pr / t_pr)
        else:
            y = (D * p_pr) / denominator

            if abs(y - 1.0) < 1e-10:  # Avoid division by zero
                logger.warning(
                    f"Using fallback correlation for Z-factor at pressure Psr={p_pr} and temperature Tsr={t_pr}"
                )
                # print(f"avoiding division by zero. Using fallback correlation. y={y}")
                z = 1.0
            else:
                numerator = D * p_pr * (1 + y + y**2 - y**3)
                denominator = (D * p_pr + E * y**2 - F * y**G) * (1 - y) ** 3

                # Check if denominator is valid
                if abs(denominator) < 1e-10:
                    z = 1.0 - (0.3 * p_pr / t_pr)  # Fallback correlation
                    logger.warning(
                        f"Denominator is not a real, finite number. Using fallback correlation. denominator={denominator}"
                    )
                else:
                    z = numerator / denominator

                    # Check if result is a real, finite number
                    if not (isinstance(z, float) and math.isfinite(z)):
                        z = 1.0 - (0.3 * p_pr / t_pr)  # Fallback correlation
                        logger.warning(f"Z is not a real, finite number. Using fallback correlation. z={z}")

    except (ValueError, ZeroDivisionError, OverflowError):
        # Fallback to a simple correlation if calculation fails
        logger.warning(f"Calculation failed. Using fallback correlation. p_pr={p_pr} and t_pr={t_pr}")
        z = 1.0 - (0.3 * p_pr / t_pr)

    return z


def calculate_z_factor_explicit_with_sour_gas_correction(fluid: "Fluid", pressure: float, temperature: float) -> float:
    """
    Calculate the compressibility factor (Z) using the linearized Z-factor correlation
    with CO2 content correction (Wichert and Aziz correction).

    Args:
        fluid: The fluid to calculate Z-factor for
        pressure: Pressure in bara
        temperature: Temperature in Kelvin

    Returns:
        Z-factor (dimensionless)
    """
    # Calculate pseudo-critical properties
    tc_mix, pc_mix, _ = calculate_pseudo_critical_properties(fluid)

    # Get CO2 fraction for Wichert and Aziz correction (No H2S in the composition)
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
    z = calculate_z_factor_explicit(t_pr, p_pr)

    return z


def solve_rachford_rice(
    z_composition: dict, k_values: dict, max_iterations: int = 100, tolerance: float = 1e-5
) -> float:
    """
    Solve the Rachford-Rice equation to find the vapor fraction.

    The Rachford-Rice equation is used to calculate the vapor fraction in a
    two-phase flash calculation. It is represented as:

    Σ (z_i * (K_i - 1)) / (1 + V * (K_i - 1)) = 0

    where z_i is the overall mole fraction of component i,
    K_i is the K-value (equilibrium ratio) of component i,
    and V is the vapor fraction.

    Args:
        z_composition: Overall composition (mole fractions)
        k_values: Equilibrium constants for each component
        max_iterations: Maximum number of iterations
        tolerance: Convergence tolerance

    Returns:
        Vapor fraction (between 0 and 1)
    """
    # Filter out components with no composition or K-values
    valid_components = {comp: z_i for comp, z_i in z_composition.items() if comp in k_values and z_i > 0}

    if not valid_components:
        return 0.5  # Default to 50% vapor if no valid components

    # Initial guess for vapor fraction
    v_min = 0.0
    v_max = 1.0
    v = 0.5  # Start with 50% vapor

    # Newton-Raphson iteration to solve Rachford-Rice
    for _ in range(max_iterations):
        f = 0.0
        df = 0.0

        for component, z_i in valid_components.items():
            k_i = k_values[component]
            term = z_i * (k_i - 1) / (1 + v * (k_i - 1))
            f += term
            df -= z_i * (k_i - 1) ** 2 / (1 + v * (k_i - 1)) ** 2

        # Check for convergence
        if abs(f) < tolerance:
            break

        # Update vapor fraction using Newton-Raphson
        v_new = v - f / df if df != 0 else 0.5

        # Bound vapor fraction between 0 and 1
        if v_new < v_min:
            v_new = v_min
        elif v_new > v_max:
            v_new = v_max

        # Check for convergence by vapor fraction change
        if abs(v_new - v) < tolerance:
            v = v_new
            break

        v = v_new

    # Ensure vapor fraction is between 0 and 1
    v = max(0.0, min(1.0, v))

    return v


def calculate_phase_compositions(z_composition: dict, k_values: dict, vapor_fraction: float) -> tuple[dict, dict]:
    """
    Calculate the compositions of the liquid and vapor phases.

    Args:
        z_composition: Overall composition (mole fractions)
        k_values: Equilibrium constants for each component
        vapor_fraction: Vapor fraction

    Returns:
        Tuple of (liquid_composition, vapor_composition)
    """
    liquid_composition = {}
    vapor_composition = {}

    for component, z_i in z_composition.items():
        if component in k_values:
            k_i = k_values[component]
            # Calculate liquid phase composition
            x_i = z_i / (1 + vapor_fraction * (k_i - 1))
            # Calculate vapor phase composition
            y_i = k_i * x_i

            liquid_composition[component] = x_i
            vapor_composition[component] = y_i

    # Normalize compositions to ensure they sum to 1
    liquid_sum = sum(liquid_composition.values())
    vapor_sum = sum(vapor_composition.values())

    if liquid_sum > 0:
        liquid_composition = {k: v / liquid_sum for k, v in liquid_composition.items()}

    if vapor_sum > 0:
        vapor_composition = {k: v / vapor_sum for k, v in vapor_composition.items()}

    return liquid_composition, vapor_composition
