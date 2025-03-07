"""
Phase equilibrium utilities for thermodynamic calculations in the process domain.

This module contains functions for phase equilibrium calculations, including:
- Wilson's equation for K-values estimation
- Rachford-Rice equation solver using Nielsen-Lia transformation
- PT flash calculation
"""

import math
from typing import TYPE_CHECKING, Optional

from libecalc.common.logger import logger
from libecalc.domain.process.core.stream.eos import calculate_Z_factors, fugacity_coefficient, mixture_parameters
from libecalc.domain.process.core.stream.thermo_constants import ThermodynamicConstants

if TYPE_CHECKING:
    from libecalc.domain.process.core.stream.fluid import Fluid


def calculate_wilson_k_values(fluid: "Fluid", pressure: float, temperature: float) -> dict:
    """
    Calculate initial K-values using Wilson's equation.

    K_i = (P_c,i/P) * exp[5.37(1+ω_i)(1-T_c,i/T)]

    Wilson's equation provides a good initial estimate for equilibrium K-values
    based on critical properties and acentric factor, which can improve
    convergence speed and stability in PT flash calculations.

    Args:
        fluid: Fluid object containing composition and component properties
        pressure: System pressure in bara
        temperature: System temperature in K

    Returns:
        Dictionary of K-values for each component
    """
    k_values = {}
    composition_dict = fluid.composition.model_dump()

    for component, mole_fraction in composition_dict.items():
        if mole_fraction > 0 and component in ThermodynamicConstants.CRITICAL_PROPERTIES:
            pc = ThermodynamicConstants.CRITICAL_PROPERTIES[component]["Pc"]
            tc = ThermodynamicConstants.CRITICAL_PROPERTIES[component]["Tc"]
            omega = ThermodynamicConstants.CRITICAL_PROPERTIES[component]["omega"]

            # Wilson's equation
            k_i = (pc / pressure) * math.exp(5.37 * (1 + omega) * (1 - tc / temperature))
            k_values[component] = k_i

    return k_values


def solve_rachford_rice(
    z_composition: dict,
    k_values: dict,
    initial_vapor_fraction: float = 0.5,
    max_iterations: int = 100,
    tolerance: float = 1e-5,
) -> tuple[float, dict, dict]:
    """
    Solve the Rachford-Rice equation using the Nielsen-Lia transformation method.

    This implementation is based on the paper:
    "Avoiding Round-Off Error in the Rachford-Rice Equation" (2021) by Markus H. Nielsen and Henrik Lia.

    The Nielsen-Lia transformation provides improved numerical stability, especially near
    phase boundaries where traditional methods struggle with round-off errors.

    Args:
        z_composition: Overall composition (mole fractions)
        k_values: Equilibrium constants for each component
        initial_vapor_fraction: Initial guess for vapor fraction
        max_iterations: Maximum number of iterations
        tolerance: Convergence tolerance

    Returns:
        Tuple of (vapor_fraction, liquid_composition, vapor_composition)
    """
    # Filter valid components and create lists for calculations
    valid_components = [comp for comp in z_composition if comp in k_values]

    if not valid_components:
        logger.warning("No valid components with K-values found. Returning all vapor phase.")
        return 1.0, {}, z_composition.copy()

    # Quick check for single-phase systems
    k_min = min(k_values[comp] for comp in valid_components)
    k_max = max(k_values[comp] for comp in valid_components)

    # All components prefer vapor phase
    if k_min >= 1.0:
        return 1.0, {comp: 0.0 for comp in z_composition}, z_composition.copy()

    # All components prefer liquid phase
    if k_max <= 1.0:
        return 0.0, z_composition.copy(), {comp: 0.0 for comp in z_composition}

    # Calculate function value at initial guess to determine if we're near vapor or liquid
    initial_sum = 0.0
    for comp in valid_components:
        z_i = z_composition[comp]
        k_i = k_values[comp]
        initial_sum += z_i * (k_i - 1.0) / (1.0 + initial_vapor_fraction * (k_i - 1.0))

    # Near vapor solution if function value is positive
    if initial_sum > 0:
        near_vapor_solution = True
        molar_fraction = 1.0 - initial_vapor_fraction  # Liquid fraction
        k_inverted = {comp: 1.0 / k_values[comp] for comp in valid_components}
    else:
        near_vapor_solution = False
        molar_fraction = initial_vapor_fraction  # Vapor fraction
        k_inverted = k_values

    # Calculate c_i = 1 / (1 - k_i)
    c_values = {}
    for comp in valid_components:
        k_i = k_inverted[comp]
        if abs(k_i - 1.0) < 1e-10:  # Protect against division by zero
            c_values[comp] = float("inf") if k_i >= 1.0 else float("-inf")
        else:
            c_values[comp] = 1.0 / (1.0 - k_i)

    # Calculate boundaries for molar fraction
    min_molar_fraction = 1.0 / (1.0 - k_max)
    max_molar_fraction = 1.0 / (1.0 - k_min)

    # Ensure molar_fraction is within bounds
    molar_fraction = max(min_molar_fraction + tolerance, min(max_molar_fraction - tolerance, molar_fraction))

    # Calculate B transformation variable
    b = 1.0 / (molar_fraction - min_molar_fraction)

    # Find boundaries for B
    b_min = 1.0 / (max_molar_fraction - min_molar_fraction)
    b_max = 1.0 / tolerance  # Approximation of infinity

    # Newton-Raphson iteration with B transformation
    for _ in range(max_iterations):
        # Calculate transformed Rachford-Rice and its derivative
        b_transformed_rr = 0.0
        b_transformed_rr_derivative = 0.0

        for comp in valid_components:
            z_i = z_composition[comp]
            c_i = c_values[comp]
            denominator = 1.0 + b * (min_molar_fraction - c_i)
            b_transformed_rr += z_i / denominator
            b_transformed_rr_derivative += z_i / (denominator * denominator)

        b_transformed_rr *= b

        # Check for convergence
        transformed_value = 0.0
        for comp in valid_components:
            z_i = z_composition[comp]
            c_i = c_values[comp]
            transformed_value += z_i / (molar_fraction - c_i)

        if abs(transformed_value) < tolerance:
            break

        # Update bounds based on function value
        if b_transformed_rr > 0:
            b_max = b
        else:
            b_min = b

        # Newton-Raphson step
        b_updated = b - b_transformed_rr / b_transformed_rr_derivative

        # Safety step if outside boundaries
        if b_updated < b_min or b_updated > b_max:
            b_updated = (b_min + b_max) / 2.0

        b = b_updated
        molar_fraction = min_molar_fraction + 1.0 / b  # Update molar fraction from B

    # Calculate phase compositions
    liquid_composition = {}
    vapor_composition = {}

    if near_vapor_solution:
        vapor_fraction = 1.0 - molar_fraction  # molar_fraction is liquid fraction

        # Calculate phase compositions using u-variable
        for comp in valid_components:
            z_i = z_composition[comp]
            c_i = c_values[comp]
            denominator = 1.0 + b * (min_molar_fraction - c_i)
            liquid_composition[comp] = -b * (z_i * c_i / denominator)
            vapor_composition[comp] = liquid_composition[comp] / k_inverted[comp]
    else:
        vapor_fraction = molar_fraction  # molar_fraction is vapor fraction

        # Calculate phase compositions using u-variable
        for comp in valid_components:
            z_i = z_composition[comp]
            c_i = c_values[comp]
            denominator = 1.0 + b * (min_molar_fraction - c_i)
            liquid_composition[comp] = -b * (z_i * c_i / denominator)
            vapor_composition[comp] = liquid_composition[comp] * k_values[comp]

    # Normalize compositions
    liquid_sum = sum(liquid_composition.values())
    vapor_sum = sum(vapor_composition.values())

    if liquid_sum > 0:
        liquid_composition = {comp: frac / liquid_sum for comp, frac in liquid_composition.items()}

    if vapor_sum > 0:
        vapor_composition = {comp: frac / vapor_sum for comp, frac in vapor_composition.items()}

    # Add any missing components with zero concentration
    for comp in z_composition:
        if comp not in liquid_composition:
            liquid_composition[comp] = 0.0
        if comp not in vapor_composition:
            vapor_composition[comp] = 0.0

    # Ensure vapor fraction is between 0 and 1
    vapor_fraction = max(0.0, min(1.0, vapor_fraction))

    return vapor_fraction, liquid_composition, vapor_composition


def michelsen_stability_test(
    composition: dict,
    temperature: float,
    pressure: float,
    vapor_test: bool = True,
    max_iterations: int = 50,
    tolerance: float = 1e-6,
) -> bool:
    """Perform Michelsen's phase stability test.

    Tests if a phase with the given composition is stable or if it will split into two phases.
    Performs either a vapor-like or liquid-like test depending on the vapor_test parameter.

    This simpler implementation determines instability when the sum of incipient phase
    mole fractions exceeds 1.0, which indicates that the current phase is unstable
    and will split into two phases.

    Args:
        composition: Dictionary of component mole fractions
        temperature: Temperature in Kelvin
        pressure: Pressure in bara
        vapor_test: If True, test for vapor-like instability, otherwise test for liquid-like instability
        max_iterations: Maximum number of iterations for stability calculations
        tolerance: Convergence tolerance

    Returns:
        True if the phase is unstable (will split), False if stable
    """
    # Get components with non-zero compositions
    components = [comp for comp, z in composition.items() if z > 0]

    if not components:
        return False

    # Convert dictionary to array for easier operations
    z = [composition[comp] for comp in components]

    # Normalize composition
    z_sum = sum(z)
    z = [zi / z_sum for zi in z]

    # Calculate reference fugacity coefficients for the current phase
    a_mix, b_mix, a_values, b_values = mixture_parameters(
        {comp: z[i] for i, comp in enumerate(components)}, temperature
    )

    # Calculate Z-factor for the reference phase
    Z_vapor, Z_liquid = calculate_Z_factors(
        a_mix * pressure / (ThermodynamicConstants.R_J_PER_MOL_K * temperature) ** 2,
        b_mix * pressure / (ThermodynamicConstants.R_J_PER_MOL_K * temperature),
    )

    # Choose the appropriate Z-factor for the reference phase
    Z_ref = Z_vapor if vapor_test else Z_liquid

    # Calculate reference fugacity coefficients
    phi_ref = {}
    for i, comp in enumerate(components):
        phi_ref[comp] = fugacity_coefficient(
            i,
            components,
            {comp: z[i] for i, comp in enumerate(components)},
            temperature,
            pressure,
            Z_ref,
            a_mix,
            b_mix,
            a_values,
            b_values,
        )

    # Initialize K-values
    # For vapor test, use Wilson K-values; for liquid test, use inverse Wilson K-values
    from libecalc.common.fluid import EoSModel, FluidComposition
    from libecalc.domain.process.core.stream.fluid import Fluid

    # Create a proper FluidComposition object
    fluid_composition = FluidComposition(**{comp: composition[comp] for comp in components if comp in composition})
    dummy_fluid = Fluid(composition=fluid_composition, eos_model=EoSModel.PR)

    k_wilson = calculate_wilson_k_values(dummy_fluid, pressure, temperature)

    # Initialize ln(K) values
    ln_k = []
    for comp in components:
        if vapor_test:
            ln_k.append(math.log(k_wilson.get(comp, 1.0)))
        else:
            ln_k.append(math.log(1.0 / k_wilson.get(comp, 1.0)))

    # Iteration for stability test
    for _ in range(max_iterations):
        # Calculate K-values and incipient phase composition
        k = [math.exp(ln_ki) for ln_ki in ln_k]
        y = [z[i] * k[i] for i in range(len(components))]
        sum_y = sum(y)

        # Normalize incipient phase composition
        y_norm = [yi / sum_y for yi in y]

        # Calculate fugacity coefficients for incipient phase
        a_mix_incipient, b_mix_incipient, a_values_incipient, b_values_incipient = mixture_parameters(
            {comp: y_norm[i] for i, comp in enumerate(components)}, temperature
        )

        Z_vapor_incipient, Z_liquid_incipient = calculate_Z_factors(
            a_mix_incipient * pressure / (ThermodynamicConstants.R_J_PER_MOL_K * temperature) ** 2,
            b_mix_incipient * pressure / (ThermodynamicConstants.R_J_PER_MOL_K * temperature),
        )

        Z_incipient = Z_vapor_incipient if vapor_test else Z_liquid_incipient

        phi_incipient = {}
        for i, comp in enumerate(components):
            phi_incipient[comp] = fugacity_coefficient(
                i,
                components,
                {comp: y_norm[i] for i, comp in enumerate(components)},
                temperature,
                pressure,
                Z_incipient,
                a_mix_incipient,
                b_mix_incipient,
                a_values_incipient,
                b_values_incipient,
            )

        # Calculate fugacity ratio and update ln(K)
        max_change = 0.0
        for i, comp in enumerate(components):
            # r = (phi_ref / phi_incipient) / sum_y
            r = (phi_ref[comp] / phi_incipient[comp]) / sum_y
            # Update ln(K)
            ln_k_new = ln_k[i] + math.log(r)
            max_change = max(max_change, abs(ln_k_new - ln_k[i]))
            ln_k[i] = ln_k_new

        # Check for convergence
        if max_change < tolerance:
            break

    # Final calculation of sum_y to determine stability
    k = [math.exp(ln_ki) for ln_ki in ln_k]
    y = [z[i] * k[i] for i in range(len(components))]
    sum_y = sum(y)

    # sum_y > 1.0 indicates instability (the phase will split)
    return sum_y > 1.0


def iterative_k_value_flash(
    composition: dict,
    temperature: float,
    pressure: float,
    initial_k_values: Optional[dict] = None,
    max_iterations: int = 30,
    tolerance: float = 1e-6,
) -> tuple[float, dict, dict]:
    """Perform iterative K-value flash calculation.

    Uses successive substitution to update K-values based on fugacity coefficients
    until convergence.

    Args:
        composition: Dictionary of component mole fractions
        temperature: Temperature in Kelvin
        pressure: Pressure in bara
        initial_k_values: Initial guess for K-values (Wilson K-values if None)
        max_iterations: Maximum number of iterations for K-value updates
        tolerance: Convergence tolerance

    Returns:
        Tuple of (vapor_fraction, liquid_composition, vapor_composition)
    """
    components = [comp for comp, z in composition.items() if z > 0]

    if not components:
        return 0.0, {}, {}

    # Initialize K-values
    if initial_k_values is None:
        # Create a dummy fluid with the given composition for Wilson K calculation
        from libecalc.common.fluid import EoSModel, FluidComposition
        from libecalc.domain.process.core.stream.fluid import Fluid

        # Create a proper FluidComposition object
        fluid_composition = FluidComposition(**{comp: composition[comp] for comp in components if comp in composition})
        dummy_fluid = Fluid(composition=fluid_composition, eos_model=EoSModel.PR)

        k_values = calculate_wilson_k_values(dummy_fluid, pressure, temperature)
    else:
        k_values = initial_k_values.copy()

    # Initial flash calculation
    initial_vf = 0.5
    vapor_fraction, x_liquid, y_vapor = solve_rachford_rice(composition, k_values, initial_vf)

    # Iterative update of K-values
    for _iteration in range(max_iterations):
        # Calculate fugacity coefficients for each phase
        # Liquid phase
        a_mix_liq, b_mix_liq, a_values_liq, b_values_liq = mixture_parameters(x_liquid, temperature)
        Z_vapor_liq, Z_liquid_liq = calculate_Z_factors(
            a_mix_liq * pressure / (ThermodynamicConstants.R_J_PER_MOL_K * temperature) ** 2,
            b_mix_liq * pressure / (ThermodynamicConstants.R_J_PER_MOL_K * temperature),
        )

        phi_liquid = {}
        for i, comp in enumerate(components):
            if comp in x_liquid and x_liquid[comp] > 0:
                phi_liquid[comp] = fugacity_coefficient(
                    i,
                    components,
                    x_liquid,
                    temperature,
                    pressure,
                    Z_liquid_liq,
                    a_mix_liq,
                    b_mix_liq,
                    a_values_liq,
                    b_values_liq,
                )
            else:
                phi_liquid[comp] = 1.0

        # Vapor phase
        a_mix_vap, b_mix_vap, a_values_vap, b_values_vap = mixture_parameters(y_vapor, temperature)
        Z_vapor_vap, Z_liquid_vap = calculate_Z_factors(
            a_mix_vap * pressure / (ThermodynamicConstants.R_J_PER_MOL_K * temperature) ** 2,
            b_mix_vap * pressure / (ThermodynamicConstants.R_J_PER_MOL_K * temperature),
        )

        phi_vapor = {}
        for i, comp in enumerate(components):
            if comp in y_vapor and y_vapor[comp] > 0:
                phi_vapor[comp] = fugacity_coefficient(
                    i,
                    components,
                    y_vapor,
                    temperature,
                    pressure,
                    Z_vapor_vap,
                    a_mix_vap,
                    b_mix_vap,
                    a_values_vap,
                    b_values_vap,
                )
            else:
                phi_vapor[comp] = 1.0

        # Update K-values based on fugacity coefficients
        new_k_values = {}
        max_k_diff = 0.0

        for comp in components:
            # K = phi_liquid / phi_vapor
            if comp in phi_vapor and phi_vapor[comp] > 0:
                new_k = phi_liquid[comp] / phi_vapor[comp]
                # Apply dampening to prevent oscillation
                damping_factor = 0.5
                new_k_values[comp] = damping_factor * new_k + (1 - damping_factor) * k_values.get(comp, new_k)
                max_k_diff = max(max_k_diff, abs(new_k_values[comp] - k_values.get(comp, 0)))
            else:
                new_k_values[comp] = k_values.get(comp, 1.0)

        # Update K-values
        k_values = new_k_values

        # Check for convergence
        if max_k_diff < tolerance:
            break

        # Solve Rachford-Rice with updated K-values
        vapor_fraction, x_liquid, y_vapor = solve_rachford_rice(composition, k_values, vapor_fraction)

    return vapor_fraction, x_liquid, y_vapor


def pt_flash(fluid: "Fluid", pressure: float, temperature: float) -> tuple[float, dict, dict]:
    """Perform a PT flash calculation to determine vapor fraction and phase compositions.

    Enhanced version that uses Michelsen stability test to determine if the mixture will
    split into two phases, and performs iterative K-value updates for better accuracy.

    The flash calculation follows these steps:
    1. Check for phase stability using Michelsen's test
    2. If unstable, perform iterative flash with K-value updates
    3. If stable, return single-phase composition

    Args:
        fluid: Fluid object with composition
        pressure: Pressure in bara
        temperature: Temperature in Kelvin

    Returns:
        Tuple of (vapor_fraction, liquid_composition, vapor_composition)
    """
    # Get composition
    composition = fluid.composition.model_dump()

    # Filter out non-component attributes and zero values
    composition = {
        comp: value
        for comp, value in composition.items()
        if not comp.startswith("_") and isinstance(value, int | float) and value > 0
    }

    # Check if we have a valid composition
    if not composition:
        return 0.0, {}, {}  # Default to liquid if no valid components

    # Initialize K-values using Wilson's equation for initial stability test
    wilson_k_values = calculate_wilson_k_values(fluid, pressure, temperature)

    # Perform Michelsen stability tests
    vapor_unstable = michelsen_stability_test(composition, temperature, pressure, vapor_test=True)
    liquid_unstable = michelsen_stability_test(composition, temperature, pressure, vapor_test=False)

    # If either test indicates instability, perform two-phase flash
    if vapor_unstable or liquid_unstable:
        # Get initial K-values using Wilson's equation
        initial_k_values = wilson_k_values

        # Perform iterative K-value flash
        return iterative_k_value_flash(composition, temperature, pressure, initial_k_values)
    else:
        # Check K-values to determine if liquid or vapor
        k_values = wilson_k_values  # Using Wilson K-values as a quick check

        # If most components have K < 1, probably liquid
        k_values_list = list(k_values.values())
        if sum(1 for k in k_values_list if k < 1.0) > len(k_values_list) / 2:
            # Mostly liquid
            return 0.0, composition.copy(), {}
        else:
            # Mostly vapor
            return 1.0, {}, composition.copy()
