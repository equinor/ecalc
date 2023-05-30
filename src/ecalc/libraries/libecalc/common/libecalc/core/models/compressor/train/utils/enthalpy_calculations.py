"""Compressor equations from:
https://www.jmcampbell.com/tip-of-the-month/2011/11/compressor-calculations-rigorous-using-equation-of-state-vs-shortcut-method/.

Equations require compressibility (z) and heat capacity ratio (kappa) for fluid in compressor, here this is an average
of inlet and outlet z and kappa
To find outlet z and kappa, an iteration of polytropic head is performed and outlet stream and corresponding z and
kappa are updated until polytropic head converges
"""

from copy import deepcopy
from typing import Callable, List, Tuple, Union

import numpy as np
from libecalc.common.logger import logger
from libecalc.common.units import UnitConstants
from libecalc.core.models.compressor.train.fluid import FluidStream
from numpy.typing import NDArray


def calculate_enthalpy_change_head_iteration(
    inlet_pressure: NDArray[np.float64],
    outlet_pressure: NDArray[np.float64],
    inlet_temperature_kelvin: NDArray[np.float64],
    polytropic_efficiency_vs_rate_and_head_function: Callable,
    molar_mass: float,
    inlet_streams: List[FluidStream],
    inlet_actual_rate_m3_per_hour: NDArray[np.float64],
) -> Tuple[NDArray[np.float64], NDArray[np.float64]]:
    """:param inlet_pressure: Inlet pressure array [bara]
    :param outlet_pressure: Outlet pressure array [bara]
    :param inlet_temperature_kelvin: Inlet temperature array [K]
    :param polytropic_efficiency_vs_rate_and_head_function:
    :param molar_mass: Molar mass [kg/mol]
    :param inlet_streams: List of FluidStream-objects
    :param inlet_actual_rate_m3_per_hour:
    :return:
    """
    pressure_ratios = outlet_pressure / inlet_pressure
    inlet_kappa = np.asarray([stream.kappa for stream in inlet_streams])
    inlet_z = np.asarray([stream.z for stream in inlet_streams])

    # Set start values for iteration
    rel_diff = 1.0
    polytropic_heads = np.full_like(inlet_actual_rate_m3_per_hour, 0.0)
    z = deepcopy(inlet_z)
    kappa = deepcopy(inlet_kappa)
    enthalpy_change_joule_per_kg = 0

    polytropic_efficiency = polytropic_efficiency_vs_rate_and_head_function(
        inlet_actual_rate_m3_per_hour, polytropic_heads
    )

    converged = False
    i = 0
    max_iterations = 20
    expected_diff = 1e-3
    while not converged and i < max_iterations:
        polytropic_heads_previous = polytropic_heads.copy()
        """
        Calculate polytropic head given current estimate for z (compressibility) and kappa
        Calculate enthalpy change given polytropic head and efficiency
        Calculate outlet enthalpy
        Estimate outlet streams by updating inlet streams with new pressure and enthalpy
        """
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

        outlet_streams = [
            stream.set_new_pressure_and_enthalpy_change(
                new_pressure=pressure, enthalpy_change_joule_per_kg=enthalpy_change
            )
            for stream, pressure, enthalpy_change in zip(inlet_streams, outlet_pressure, enthalpy_change_joule_per_kg)
        ]

        # Get z (compressibility) and kappa (heat capacity ratio) of the estimated outlet streams
        outlet_kappa = np.asarray([stream.kappa for stream in outlet_streams])
        outlet_z = np.asarray([stream.z for stream in outlet_streams])

        # Update z and kappa estimates based on new outlet estimates
        z = (inlet_z + outlet_z) / 2
        kappa = (inlet_kappa + outlet_kappa) / 2

        # Set convergence criterion on polytropic head
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
                "calculate_enthalpy_change_head_iteration"
                f" did not converge after {max_iterations} iterations."
                f" inlet_z: {inlet_z}."
                f" inlet_kappa: {inlet_kappa}."
                f" polytropic_efficiency: {polytropic_efficiency}."
                f" pressure_ratios: {pressure_ratios}."
                f" polytropic_efficiency: {polytropic_efficiency}."
                f" Final diff between target and result was {rel_diff}, while expected convergence diff criteria is set to diff lower than {expected_diff}"
                f" NOTE! We will use as the closest result we got for target for further calculations."
                " This should normally not happen. Please contact eCalc support."
            )

    return enthalpy_change_joule_per_kg, polytropic_efficiency


def calculate_polytropic_head_campbell(
    polytropic_efficiency: Union[float, NDArray[np.float64]],
    kappa: Union[float, NDArray[np.float64]],
    z: Union[float, NDArray[np.float64]],
    molar_mass: Union[float, NDArray[np.float64]],
    pressure_ratios: Union[NDArray[np.float64], float],
    temperatures_kelvin: Union[float, NDArray[np.float64]],
) -> Union[NDArray[np.float64], float]:
    """Calculate head from pressure ratio based on "generic gas composition/temperature"
    Output unit in Joule per kg.

    :param polytropic_efficiency: Polytropic efficiency array (0, 1]
    :param kappa: Heat capacity ratio/ratio of specific heats
    :param z: Compressability
    :param molar_mass: Molar mass value or array [kg/mol]
    :param pressure_ratios: Pressure ratios between stages
    :param temperatures_kelvin: Temperature value or array [K]
    """
    # http://www.jmcampbell.com/tip-of-the-month/2011/11/compressor-calculations-rigorous-using-equation-of-state-vs-shortcut-method/ Eqn 3B  # noqa
    n_minus_1_over_n = _calculate_polytropic_exponent_expression_n_minus_1_over_n(
        kappa=kappa, polytropic_efficiency=polytropic_efficiency
    )
    polytropic_head = _calculate_head(
        exponent_expression=n_minus_1_over_n,
        temperature_kelvin=temperatures_kelvin,
        pressure_ratio=pressure_ratios,
        z=z,
        molar_mass=molar_mass,
    )

    return polytropic_head


def _calculate_head(
    exponent_expression: Union[float, NDArray[np.float64]],
    temperature_kelvin: Union[float, NDArray[np.float64]],
    pressure_ratio: Union[float, NDArray[np.float64]],
    z: Union[float, NDArray[np.float64]],
    molar_mass: Union[float, NDArray[np.float64]],
) -> NDArray[np.float64]:
    """Calculate head [J/kg].

    :param exponent_expression:
    :param temperature_kelvin: Temperature array [K]
    :param pressure_ratio: Pressure ratios between stages
    :param z: Compressability
    """
    return np.array(
        1
        / exponent_expression
        * (z * UnitConstants.GAS_CONSTANT * temperature_kelvin)
        / molar_mass
        * (pressure_ratio**exponent_expression - 1)
    )


def _calculate_polytropic_exponent_expression_n_minus_1_over_n(
    kappa: Union[float, NDArray[np.float64]],
    polytropic_efficiency: Union[float, NDArray[np.float64]],
) -> Union[float, NDArray[np.float64]]:
    """https://www.jmcampbell.com/tip-of-the-month/2011/11/compressor-calculations-rigorous-using-equation-of-state-vs-shortcut-method/ Eqn 6  # noqa
    Calculate (n-1)/n where n is the polytropic exponent.
    Use float64 to avoid ZeroDivisonError and rather get Inf.

    :param kappa: Heat capacity ratio/ratio of specific heats
    :param polytropic_efficiency: Polytropic efficiency array (0, 1]
    """
    n_minus_1_over_n = np.float64(kappa - 1.0) / np.float64(kappa * polytropic_efficiency)

    return n_minus_1_over_n


def calculate_outlet_pressure_campbell(
    kappa: Union[float, NDArray[np.float64]],
    polytropic_efficiency: Union[float, NDArray[np.float64]],
    polytropic_head_fluid_Joule_per_kg: Union[float, NDArray[np.float64]],
    molar_mass: Union[float, NDArray[np.float64]],
    z_inlet: Union[float, NDArray[np.float64]],
    inlet_temperature_K: Union[float, NDArray[np.float64]],
    inlet_pressure_bara: Union[float, NDArray[np.float64]],
) -> Union[float, NDArray[np.float64]]:
    """Calculate outlet pressure of polytropic compressor based on
    https://www.jmcampbell.com/tip-of-the-month/2011/11/compressor-calculations-rigorous-using-equation-of-state-vs-shortcut-method/ Eqn 3B  # noqa.

    If all inputs are given as floats, the output will be a float, if any of the inputs are given as an numpy array, the
    output will be an array

    :param kappa: heat capacity ratio/ratio of specific heats
    :param polytropic_efficiency: Polytropic efficiency array or value (0, 1]
    :param polytropic_head_fluid_Joule_per_kg: Polytropic head array or value [J/kg]
    :param molar_mass: Molar mass [kg/mol]
    :param z_inlet: Compressability
    :param inlet_temperature_K: Inlet temperature value or array [K]
    :param inlet_pressure_bara: Inlet pressure value or array [bara]
    """
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

    if isinstance(outlet_pressure_bara, np.ndarray):
        return np.array(outlet_pressure_bara)
    else:
        return float(outlet_pressure_bara)
