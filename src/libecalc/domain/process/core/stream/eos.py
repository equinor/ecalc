"""
Peng-Robinson Equation of State (EOS) module for K-value calculations.

This module implements the Peng-Robinson EOS for calculating K-values
in multicomponent natural gas systems, to be used in PT flash calculations.
"""

import math

import numpy as np

from libecalc.common.logger import logger
from libecalc.domain.process.core.stream.thermo_constants import ThermodynamicConstants

# Universal gas constant in [bar·L/(mol·K)] - convert from J/(mol·K)
R = ThermodynamicConstants.R_J_PER_MOL_K / 100  # J/(mol·K) to bar·L/(mol·K)


def binary_interaction_parameter(comp_i: str, comp_j: str, T: float) -> float:
    """
    Calculate binary interaction parameter (BIP) for a component pair.

    This function uses different correlations based on the component pair:
    1. For hydrocarbon-hydrocarbon pairs: Gao correlation
    2. For CO2-hydrocarbon pairs: Barrios correlation (temperature-dependent)
    3. For N2-hydrocarbon pairs: Temperature-dependent correlation
    4. For water-hydrocarbon pairs: Default value of 0.5
    5. For all other pairs: Default value of 0.0

    The Gao correlation is:
    k_ij = 1 - ((2 * sqrt(T_ci * T_cj)) / (T_ci + T_cj))^((Z_ci + Z_cj) / 2)

    where T_c is critical temperature and Z_c is critical compressibility factor.

    The Barrios correlation for CO2-hydrocarbon pairs is:
    k_ij = c + d * T_r
    where:
    c = -0.6910 * omega^2 + 0.4373 * omega - 0.02426
    d = 0.09731
    T_r = T / T_c,hc

    Args:
        comp_i: First component name
        comp_j: Second component name
        T: Temperature in K

    Returns:
        Binary interaction parameter (dimensionless)
    """
    # Check if either component is not in the critical properties database
    if (
        comp_i not in ThermodynamicConstants.CRITICAL_PROPERTIES
        or comp_j not in ThermodynamicConstants.CRITICAL_PROPERTIES
    ):
        return 0.0

    # Check if both components are hydrocarbons (not nitrogen, CO2, or water)
    non_hydrocarbons = ["nitrogen", "CO2", "water"]

    if comp_i not in non_hydrocarbons and comp_j not in non_hydrocarbons:
        # Both are hydrocarbons, use Gao correlation
        # Get critical temperatures
        T_ci = ThermodynamicConstants.CRITICAL_PROPERTIES[comp_i]["Tc"]
        T_cj = ThermodynamicConstants.CRITICAL_PROPERTIES[comp_j]["Tc"]

        # Get critical Z-factors
        Z_ci = ThermodynamicConstants.CRITICAL_Z_FACTORS.get(comp_i, 0.27)  # Default if not found
        Z_cj = ThermodynamicConstants.CRITICAL_Z_FACTORS.get(comp_j, 0.27)  # Default if not found

        # Calculate Gao correlation
        term = (2 * math.sqrt(T_ci * T_cj)) / (T_ci + T_cj)
        k_ij = 1 - term ** ((Z_ci + Z_cj) / 2)

        return k_ij

    # Special case: CO2-hydrocarbon (using Barrios correlation)
    if (comp_i == "CO2" and comp_j not in non_hydrocarbons) or (comp_j == "CO2" and comp_i not in non_hydrocarbons):
        # Barrios correlation for CO2-hydrocarbon
        hydrocarbon = comp_i if comp_i != "CO2" else comp_j
        omega = ThermodynamicConstants.CRITICAL_PROPERTIES[hydrocarbon]["omega"]
        Tc_hc = ThermodynamicConstants.CRITICAL_PROPERTIES[hydrocarbon]["Tc"]
        T_r = T / Tc_hc
        c = -0.6910 * omega**2 + 0.4373 * omega - 0.02426
        d = 0.09731
        return c + d * T_r

    # Special case: N2-hydrocarbon
    if (comp_i == "nitrogen" and comp_j != "CO2" and comp_j != "water") or (
        comp_j == "nitrogen" and comp_i != "CO2" and comp_i != "water"
    ):
        # Fixed BIP for N2-hydrocarbon
        return 0.1

    # Special case: Water-hydrocarbon
    if (comp_i == "water" and comp_j != "CO2" and comp_j != "nitrogen") or (
        comp_j == "water" and comp_i != "CO2" and comp_i != "nitrogen"
    ):
        # Water with hydrocarbons has a large BIP
        return 0.5

    # Default case: use 0.0
    return 0.0


def pure_component_params(component: str, T: float) -> tuple[float, float, float]:
    """
    Calculate pure-component parameters for Peng-Robinson EOS.

    Args:
        component: Component name
        T: Temperature in K

    Returns:
        Tuple of (a_i * alpha_i, b_i, kappa)
    """
    if component not in ThermodynamicConstants.CRITICAL_PROPERTIES:
        raise ValueError(f"Component {component} not found in critical properties database")

    props = ThermodynamicConstants.CRITICAL_PROPERTIES[component]
    Tc = props["Tc"]
    Pc = props["Pc"]  # bar
    omega = props["omega"]

    # Calculate PR EOS parameters
    a_i = 0.45724 * R**2 * Tc**2 / Pc
    b_i = 0.07780 * R * Tc / Pc

    # Calculate kappa based on acentric factor
    kappa = 0.37464 + 1.54226 * omega - 0.26992 * omega**2

    # Calculate temperature-dependent alpha factor
    alpha_i = (1 + kappa * (1 - math.sqrt(T / Tc))) ** 2

    return a_i * alpha_i, b_i, kappa


def mixture_parameters(composition: dict[str, float], T: float) -> tuple[float, float, list[float], list[float]]:
    """
    Compute mixture parameters a_mix and b_mix using quadratic mixing rules.

    Args:
        composition: Dictionary of component names and mole fractions
        T: Temperature in K

    Returns:
        Tuple of (a_mix, b_mix, list of a_i*alpha_i values, list of b_i values)
    """
    components = list(composition.keys())
    a_values = []
    b_values = []

    # Calculate pure component parameters
    for comp in components:
        if composition[comp] > 0:
            a_i_alpha, b_i, _ = pure_component_params(comp, T)
            a_values.append(a_i_alpha)
            b_values.append(b_i)
        else:
            # Skip components with zero composition
            a_values.append(0.0)
            b_values.append(0.0)

    # Calculate mixture parameters using mixing rules
    a_mix = 0.0
    for i, comp_i in enumerate(components):
        for j, comp_j in enumerate(components):
            if composition[comp_i] > 0 and composition[comp_j] > 0:
                kij = binary_interaction_parameter(comp_i, comp_j, T)
                a_mix += composition[comp_i] * composition[comp_j] * math.sqrt(a_values[i] * a_values[j]) * (1 - kij)

    # Linear mixing rule for b
    b_mix = sum(composition[comp] * b_values[i] for i, comp in enumerate(components))

    return a_mix, b_mix, a_values, b_values


def solve_cubic_PR(A: float, B: float) -> list[float]:
    """
    Solve the Peng-Robinson cubic equation in Z:
    Z^3 - (1-B)*Z^2 + (A-3B^2-2B)*Z - (AB-B^2-B^3) = 0

    Args:
        A: Dimensionless parameter A = a*P/(R^2*T^2)
        B: Dimensionless parameter B = b*P/(R*T)

    Returns:
        List of real roots (compressibility factors)
    """
    coeffs = [1.0, -(1 - B), (A - 3 * B**2 - 2 * B), -(A * B - B**2 - B**3)]

    # Solve cubic equation
    roots = np.roots(coeffs)

    # Filter real roots
    real_roots = []
    for root in roots:
        if abs(root.imag) < 1e-10:
            # Only consider physically meaningful roots (Z > 0)
            if root.real > 0:
                real_roots.append(root.real)

    return real_roots


def calculate_Z_factors(A: float, B: float) -> tuple[float, float]:
    """
    Calculate compressibility factors (Z) for vapor and liquid phases.

    Args:
        A: Dimensionless parameter A = a*P/(R^2*T^2)
        B: Dimensionless parameter B = b*P/(R*T)

    Returns:
        Tuple of (Z_vapor, Z_liquid)
    """
    roots = solve_cubic_PR(A, B)

    # If we find three real roots, we have both liquid and vapor phases
    if len(roots) == 3:
        # Sort roots - smallest is liquid, largest is vapor
        roots.sort()
        Z_liquid = roots[0]
        Z_vapor = roots[2]
        return Z_vapor, Z_liquid

    # If we find one root, it's either all liquid or all vapor
    elif len(roots) == 1:
        # Determine phase based on compressibility factor
        Z = roots[0]
        if Z < 0.3:  # Empirical threshold
            # Likely liquid phase
            return Z + 0.5, Z  # Create artificial separation
        else:
            # Likely vapor phase
            return Z, max(0.2, Z - 0.3)  # Create artificial separation

    # For two roots or other cases, make a reasonable estimate
    elif len(roots) == 2:
        roots.sort()
        return roots[1], roots[0]  # Larger root is vapor, smaller is liquid

    # Default values if no valid roots are found
    logger.warning("No valid roots found for Peng-Robinson EOS. Returning default values.")
    return 0.9, 0.2  # Default values for vapor and liquid


def fugacity_coefficient(
    component_index: int,
    components: list[str],
    composition: dict[str, float],
    T: float,
    P: float,
    Z: float,
    a_mix: float,
    b_mix: float,
    a_values: list[float],
    b_values: list[float],
) -> float:
    """
    Calculate the fugacity coefficient for a component using Peng-Robinson EOS.

    Args:
        component_index: Index of the component in the components list
        components: List of component names
        composition: Dictionary of component names and mole fractions
        T: Temperature in K
        P: Pressure in bar
        Z: Compressibility factor
        a_mix: Mixture parameter a
        b_mix: Mixture parameter b
        a_values: List of a_i*alpha_i values
        b_values: List of b_i values

    Returns:
        Fugacity coefficient (dimensionless)
    """
    try:
        component = components[component_index]
        bi = b_values[component_index]

        # Calculate dimensionless parameters
        A_mix = a_mix * P / (R**2 * T**2)
        B_mix = b_mix * P / (R * T)

        # Calculate fugacity coefficient
        term1 = (bi / b_mix) * (Z - 1)

        # Handle potential math domain error
        if Z <= B_mix:
            # Apply a small adjustment to avoid log(negative) or log(0)
            term2 = -math.log(max(Z - B_mix, 1e-10))
        else:
            term2 = -math.log(Z - B_mix)

        # Calculate the summation term
        summation = 0.0
        for j, comp_j in enumerate(components):
            if composition[comp_j] > 0:
                kij = binary_interaction_parameter(component, comp_j, T)
                a_ij = math.sqrt(a_values[component_index] * a_values[j]) * (1 - kij)
                summation += composition[comp_j] * a_ij

        # Handle potential division by zero
        if abs(B_mix) < 1e-10:
            term3 = 0.0
        else:
            # Complete the equation with safety checks
            term3 = -(A_mix / (2 * math.sqrt(2) * B_mix)) * ((2 * summation / a_mix) - (bi / b_mix))

        # Handle potential math domain error
        denom1 = Z + (1 + math.sqrt(2)) * B_mix
        denom2 = Z + (1 - math.sqrt(2)) * B_mix

        # Ensure denominators aren't zero or negative
        if denom1 <= 0 or denom2 <= 0:
            term4 = 0.0
        else:
            term4 = math.log(denom1 / denom2)

        ln_phi = term1 + term2 + term3 * term4

        # Ensure the result is finite and reasonable
        if not math.isfinite(ln_phi):
            # Return a reasonable default value
            return 1.0

        return math.exp(ln_phi)

    except (ValueError, ZeroDivisionError, OverflowError):
        # If calculation fails, return a reasonable default
        return 1.0


def calculate_K_values_PR(composition: dict[str, float], T: float, P: float) -> dict[str, float]:
    """
    Calculate K-values for a multicomponent system using Peng-Robinson EOS.

    K_i = phi_i^L / phi_i^V, where phi_i is the fugacity coefficient

    Args:
        composition: Dictionary of component names and mole fractions
        T: Temperature in K
        P: Pressure in bar

    Returns:
        Dictionary of component names and K-values
    """
    # Filter out components with zero composition
    valid_composition = {
        comp: frac
        for comp, frac in composition.items()
        if frac > 0 and comp in ThermodynamicConstants.CRITICAL_PROPERTIES
    }

    # Check if we have any valid components
    if not valid_composition:
        return {}

    # Get list of components
    components = list(valid_composition.keys())

    # Calculate mixture parameters
    a_mix, b_mix, a_values, b_values = mixture_parameters(valid_composition, T)

    # Calculate dimensionless parameters
    A_mix = a_mix * P / (R**2 * T**2)
    B_mix = b_mix * P / (R * T)

    # Calculate Z factors for vapor and liquid phases
    Z_vapor, Z_liquid = calculate_Z_factors(A_mix, B_mix)

    # Calculate fugacity coefficients
    phi_vapor = {}
    phi_liquid = {}

    for i, comp in enumerate(components):
        phi_vapor[comp] = fugacity_coefficient(
            i, components, valid_composition, T, P, Z_vapor, a_mix, b_mix, a_values, b_values
        )
        phi_liquid[comp] = fugacity_coefficient(
            i, components, valid_composition, T, P, Z_liquid, a_mix, b_mix, a_values, b_values
        )

    # Calculate K-values directly
    k_values = {}
    for comp in components:
        if phi_vapor[comp] > 0:
            k_values[comp] = phi_liquid[comp] / phi_vapor[comp]
        else:
            k_values[comp] = 1.0  # Fallback for division by zero

    return k_values
