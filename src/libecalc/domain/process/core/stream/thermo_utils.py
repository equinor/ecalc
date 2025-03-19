"""
Utilities for thermodynamic calculations in the process domain.
"""

from __future__ import annotations

import math

from libecalc.common.logger import logger
from libecalc.domain.process.core.stream.fluid import Fluid
from libecalc.domain.process.core.stream.thermo_constants import ThermodynamicConstants


def calculate_molar_mass(fluid: Fluid) -> float:
    """
    Calculate the molar mass of a fluid mixture using component molecular weights.

    Args:
        fluid: The fluid to calculate molar mass for

    Returns:
        Molar mass in kg/mol

    Raises:
        ValueError: If the fluid composition is empty or has no valid components
    """
    # Get composition as a dictionary
    composition_dict = fluid.composition.model_dump()

    # Calculate weighted sum of molecular weights
    mw_sum = 0.0
    total_mole_fraction = 0.0

    for component, mole_fraction in composition_dict.items():
        if mole_fraction > 0 and component in ThermodynamicConstants.COMPONENTS:
            mw_sum += mole_fraction * ThermodynamicConstants.COMPONENTS[component].molecular_weight_kg_per_mol
            total_mole_fraction += mole_fraction

    # Normalize if total mole fraction is not 1.0
    if total_mole_fraction > 0:
        return mw_sum / total_mole_fraction
    else:
        raise ValueError("Empty composition or no valid components found for molar mass calculation")


def calculate_pseudo_critical_properties(fluid: Fluid) -> tuple[float, float, float]:
    """
    Calculate pseudo-critical properties for a fluid mixture.

    Args:
        fluid: The fluid to calculate properties for

    Returns:
        Tuple of (Tc_pseudo, Pc_pseudo, omega_pseudo)

    Raises:
        ValueError: If the fluid composition is empty or has no valid components
    """
    composition_dict = fluid.composition.model_dump()

    # Initialize sums
    tc_sum = 0.0
    pc_sum = 0.0
    omega_sum = 0.0
    total_mole_fraction = 0.0

    # Calculate weighted sums
    for component, mole_fraction in composition_dict.items():
        if mole_fraction > 0 and component in ThermodynamicConstants.COMPONENTS:
            tc_sum += mole_fraction * ThermodynamicConstants.COMPONENTS[component].critical_temperature_k
            pc_sum += mole_fraction * ThermodynamicConstants.COMPONENTS[component].critical_pressure_bara
            omega_sum += mole_fraction * ThermodynamicConstants.COMPONENTS[component].acentric_factor
            total_mole_fraction += mole_fraction

    # Normalize if total mole fraction is not 1.0
    if total_mole_fraction > 0:
        tc_pseudo = tc_sum / total_mole_fraction
        pc_pseudo = pc_sum / total_mole_fraction
        omega_pseudo = omega_sum / total_mole_fraction
    else:
        raise ValueError("Empty composition or no valid components found for pseudo-critical properties calculation")

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
            z = 1.0 - (0.3 * p_pr / t_pr)
        else:
            y = (D * p_pr) / denominator

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


def calculate_z_factor_explicit_with_sour_gas_correction(fluid: Fluid, pressure: float, temperature: float) -> float:
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
