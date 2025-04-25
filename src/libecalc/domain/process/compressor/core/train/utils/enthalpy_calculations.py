"""Compressor equations from:
https://www.jmcampbell.com/tip-of-the-month/2011/11/compressor-calculations-rigorous-using-equation-of-state-vs-shortcut-method/.

Equations require compressibility (z) and heat capacity ratio (kappa) for fluid in compressor, here this is an average
of inlet and outlet z and kappa
To find outlet z and kappa, an iteration of polytropic head is performed and outlet stream and corresponding z and
kappa are updated until polytropic head converges
"""

from collections.abc import Callable
from copy import deepcopy

import numpy as np
from numpy.typing import NDArray

from libecalc.common.logger import logger
from libecalc.common.units import UnitConstants
from libecalc.domain.process.compressor.core.train.fluid import FluidStream


def calculate_enthalpy_change_head_iteration(
    inlet_pressure: NDArray[np.float64] | float,
    outlet_pressure: NDArray[np.float64] | float,
    inlet_temperature_kelvin: NDArray[np.float64] | float,
    polytropic_efficiency_vs_rate_and_head_function: Callable,
    molar_mass: float,
    inlet_streams: list[FluidStream] | FluidStream,
    inlet_actual_rate_m3_per_hour: NDArray[np.float64] | float,
) -> tuple[NDArray[np.float64], NDArray[np.float64]] | tuple[float, float]:
    """
    Simplified method of finding enthalpy change in compressors.

    Only used in Simplified Compressor train

    Args:
        inlet_pressure: Inlet pressure array [bara] or scalar.
        outlet_pressure: Outlet pressure array [bara] or scalar.
        inlet_temperature_kelvin: Inlet temperature array [K] or scalar.
        polytropic_efficiency_vs_rate_and_head_function: Callable for efficiency calculation.
        molar_mass: Molar mass [kg/mol].
        inlet_streams: List of FluidStream objects or a single FluidStream.
        inlet_actual_rate_m3_per_hour: Mass rate through compressor [m3/h] or scalar.

    Returns:
        Tuple of enthalpy changes [J/kg] and polytropic efficiencies [-].
    """
    # Ensure inputs are numpy arrays for consistent operations
    single_input = False
    inlet_pressure = np.atleast_1d(inlet_pressure)
    outlet_pressure = np.atleast_1d(outlet_pressure)
    inlet_temperature_kelvin = np.atleast_1d(inlet_temperature_kelvin)
    inlet_actual_rate_m3_per_hour = np.atleast_1d(inlet_actual_rate_m3_per_hour)

    if isinstance(inlet_streams, FluidStream):
        single_input = True
        inlet_streams = [inlet_streams]

    pressure_ratios = np.divide(outlet_pressure, inlet_pressure)
    inlet_kappa = np.asarray([stream.kappa for stream in inlet_streams])
    inlet_z = np.asarray([stream.z for stream in inlet_streams])

    polytropic_heads = np.full_like(inlet_actual_rate_m3_per_hour, 0.0)
    z = deepcopy(inlet_z)
    kappa = deepcopy(inlet_kappa)
    enthalpy_change_joule_per_kg = np.zeros_like(inlet_actual_rate_m3_per_hour)

    polytropic_efficiency = polytropic_efficiency_vs_rate_and_head_function(
        inlet_actual_rate_m3_per_hour, polytropic_heads
    )

    converged = False
    i = 0
    max_iterations = 20
    expected_diff = 1e-3
    while not converged and i < max_iterations:
        polytropic_heads_previous = polytropic_heads.copy()

        # Calculate polytropic head and enthalpy change
        polytropic_efficiency = polytropic_efficiency_vs_rate_and_head_function(
            inlet_actual_rate_m3_per_hour, polytropic_heads
        )
        polytropic_heads = calculate_polytropic_head_campbell(
            polytropic_efficiency=polytropic_efficiency,
            kappa=kappa,
            z=z,
            molar_mass=molar_mass,
            pressure_ratios=pressure_ratios,
            temperatures_kelvin=inlet_temperature_kelvin,
        )
        enthalpy_change_joule_per_kg = polytropic_heads / polytropic_efficiency

        # Update outlet streams
        outlet_streams = [
            stream.set_new_pressure_and_enthalpy_change(
                new_pressure=pressure, enthalpy_change_joule_per_kg=enthalpy_change
            )
            for stream, pressure, enthalpy_change in zip(inlet_streams, outlet_pressure, enthalpy_change_joule_per_kg)
        ]

        # Update z and kappa estimates
        outlet_kappa = np.asarray([stream.kappa for stream in outlet_streams])
        outlet_z = np.asarray([stream.z for stream in outlet_streams])
        z = (inlet_z + outlet_z) / 2
        kappa = (inlet_kappa + outlet_kappa) / 2

        # Convergence check
        if np.linalg.norm(polytropic_heads_previous) != 0:
            rel_diff = float(
                np.linalg.norm(polytropic_heads - polytropic_heads_previous) / np.linalg.norm(polytropic_heads_previous)
            )
        else:
            rel_diff = 1

        converged = rel_diff < expected_diff
        i += 1

        if i == max_iterations:
            logger.error(
                "calculate_enthalpy_change_head_iteration did not converge after %d iterations. "
                "Final relative difference: %f",
                max_iterations,
                rel_diff,
            )

    # If inputs were scalars, return scalars
    if not single_input:
        return enthalpy_change_joule_per_kg, polytropic_efficiency

    return float(enthalpy_change_joule_per_kg[0]), float(polytropic_efficiency[0])


def calculate_polytropic_head_campbell(
    polytropic_efficiency: float | NDArray[np.float64],
    kappa: float | NDArray[np.float64],
    z: float | NDArray[np.float64],
    molar_mass: float | NDArray[np.float64],
    pressure_ratios: NDArray[np.float64] | float,
    temperatures_kelvin: float | NDArray[np.float64],
) -> NDArray[np.float64] | float:
    """
    Calculate polytropic head for a compressor.

    Args:
        polytropic_efficiency: Polytropic efficiency array (0, 1].
        kappa: Heat capacity ratio/ratio of specific heats.
        z: Compressibility.
        molar_mass: Molar mass value or array [kg/mol].
        pressure_ratios: Pressure ratios between stages.
        temperatures_kelvin: Temperature value or array [K].

    Returns:
        Polytropic head [J/kg].
    """
    input_is_numpy = isinstance(kappa, np.ndarray)
    polytropic_efficiency = np.atleast_1d(polytropic_efficiency)
    kappa = np.atleast_1d(kappa)
    z = np.atleast_1d(z)
    molar_mass = np.atleast_1d(molar_mass)
    pressure_ratios = np.atleast_1d(pressure_ratios)
    temperatures_kelvin = np.atleast_1d(temperatures_kelvin)

    result = _calculate_head(
        exponent_expression=_calculate_polytropic_exponent_expression_n_minus_1_over_n(kappa, polytropic_efficiency),
        temperature_kelvin=temperatures_kelvin,
        pressure_ratio=pressure_ratios,
        z=z,
        molar_mass=molar_mass,
    )

    # Return scalar if inputs were scalar
    return result if input_is_numpy else result[0]


def _calculate_head(
    exponent_expression: NDArray[np.float64],
    temperature_kelvin: NDArray[np.float64],
    pressure_ratio: NDArray[np.float64],
    z: NDArray[np.float64],
    molar_mass: NDArray[np.float64],
) -> NDArray[np.float64]:
    """
    Calculate polytropic head [J/kg].

    Args:
        exponent_expression: Exponent expression (n-1)/n as a numpy array.
        temperature_kelvin: Temperature array [K].
        pressure_ratio: Pressure ratios between stages as a numpy array.
        z: Compressibility as a numpy array.
        molar_mass: Molar mass array [kg/mol].

    Returns:
        Polytropic head [J/kg] as a numpy array.
    """
    return (
        1
        / exponent_expression
        * (z * UnitConstants.GAS_CONSTANT * temperature_kelvin)
        / molar_mass
        * (pressure_ratio**exponent_expression - 1)
    )


def _calculate_polytropic_exponent_expression_n_minus_1_over_n(
    kappa: NDArray[np.float64],
    polytropic_efficiency: NDArray[np.float64],
) -> NDArray[np.float64]:
    """
    Calculate (n-1)/n where n is the polytropic exponent.

    Based on https://www.jmcampbell.com/tip-of-the-month/2011/11/compressor-calculations-rigorous-using-equation-of-state-vs-shortcut-method/ Eqn 6  # noqa

    Args:
        kappa: Heat capacity ratio/ratio of specific heats as a numpy array.
        polytropic_efficiency: Polytropic efficiency array (0, 1] as a numpy array.

    Returns:
        (n-1)/n as a numpy array, where n is the polytropic exponent.
    """
    return (kappa - 1.0) / (kappa * polytropic_efficiency)


def calculate_outlet_pressure_campbell(
    kappa: float | NDArray[np.float64],
    polytropic_efficiency: float | NDArray[np.float64],
    polytropic_head_fluid_Joule_per_kg: float | NDArray[np.float64],
    molar_mass: float | NDArray[np.float64],
    z_inlet: float | NDArray[np.float64],
    inlet_temperature_K: float | NDArray[np.float64],
    inlet_pressure_bara: float | NDArray[np.float64],
) -> float | NDArray[np.float64]:
    """
    Calculate outlet pressure of a polytropic compressor.

    Based on  https://www.jmcampbell.com/tip-of-the-month/2011/11/compressor-calculations-rigorous-using-equation-of-state-vs-shortcut-method/ Eqn 3B  # noqa.

    If all inputs are given as floats, the output will be a float, if any of the inputs are given as a numpy array, the
    output will be an array

    Args:
        kappa: Heat capacity ratio/ratio of specific heats.
        polytropic_efficiency: Polytropic efficiency array or value (0, 1].
        polytropic_head_fluid_Joule_per_kg: Polytropic head array or value [J/kg].
        molar_mass: Molar mass [kg/mol].
        z_inlet: Compressibility.
        inlet_temperature_K: Inlet temperature value or array [K].
        inlet_pressure_bara: Inlet pressure value or array [bara].

    Returns:
        Outlet pressure [bara].
    """
    input_is_numpy = isinstance(kappa, np.ndarray)
    kappa = np.atleast_1d(kappa)
    polytropic_efficiency = np.atleast_1d(polytropic_efficiency)
    polytropic_head_fluid_Joule_per_kg = np.atleast_1d(polytropic_head_fluid_Joule_per_kg)
    molar_mass = np.atleast_1d(molar_mass)
    z_inlet = np.atleast_1d(z_inlet)
    inlet_temperature_K = np.atleast_1d(inlet_temperature_K)
    inlet_pressure_bara = np.atleast_1d(inlet_pressure_bara)

    n_over_n_minus_1 = 1.0 / _calculate_polytropic_exponent_expression_n_minus_1_over_n(
        kappa=kappa, polytropic_efficiency=polytropic_efficiency
    )

    p2_p1_fraction = (
        1.0
        + polytropic_head_fluid_Joule_per_kg
        / n_over_n_minus_1
        * molar_mass
        / (z_inlet * UnitConstants.GAS_CONSTANT * inlet_temperature_K)
    ) ** (n_over_n_minus_1)
    outlet_pressure_bara = inlet_pressure_bara * p2_p1_fraction

    return outlet_pressure_bara if input_is_numpy else outlet_pressure_bara[0]
