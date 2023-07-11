from typing import Tuple

from libecalc.common.logger import logger
from libecalc.common.units import UnitConstants
from libecalc.core.models.compressor.train.fluid import FluidStream
from libecalc.core.models.compressor.train.utils.enthalpy_calculations import (
    calculate_outlet_pressure_campbell,
)

OUTLET_PRESSURE_CONVERGENCE_TOLERANCE = 1e-2
PRESSURE_CALCULATION_TOLERANCE = 1e-3
POWER_CALCULATION_TOLERANCE = 1e-3


def calculate_asv_corrected_rate(
    minimum_actual_rate_m3_per_hour: float,
    actual_rate_m3_per_hour: float,
    density_kg_per_m3,
) -> Tuple[float, float]:
    """Correct the rate with anti-surge valve (ASV)

    Ensure the flow rate through the compressor is fulfilling the minimum requirements.

    If the actual rate is below the minimum required flow rate, the requirement must be filled with recycling

    Args:
        minimum_actual_rate_m3_per_hour: Minimum required flow rate in compressor [m3/h]
        actual_rate_m3_per_hour: Actual rate before recycling [m3/h]
        density_kg_per_m3: Density of gas [kg/m3]

    Returns:
        Corrected flow rate [m3/h]
        Corrected mass rate [kg/h]

    """
    actual_rate_asv_corrected_m3_per_hour = max(actual_rate_m3_per_hour, minimum_actual_rate_m3_per_hour)
    mass_rate_asv_corrected_kg_per_hour = actual_rate_asv_corrected_m3_per_hour * density_kg_per_m3
    return (
        actual_rate_asv_corrected_m3_per_hour,
        mass_rate_asv_corrected_kg_per_hour,
    )


def calculate_power_in_megawatt(
    enthalpy_change_joule_per_kg: float,
    mass_rate_kg_per_hour: float,
) -> float:
    """Calculate power consumption of given enthalpy change (increase) on a mass flow

    Args:
        enthalpy_change_joule_per_kg:  Enthalpy change on fluid in compressor [J/kg]
        mass_rate_kg_per_hour:  Mass rate through compressor [kg/h]

    Returns:
        Power requirement [MW]

    """
    return (
        enthalpy_change_joule_per_kg
        * mass_rate_kg_per_hour
        / UnitConstants.SECONDS_PER_HOUR
        * UnitConstants.WATT_TO_MEGAWATT
    )


def calculate_outlet_pressure_and_stream(
    polytropic_efficiency: float,
    polytropic_head_joule_per_kg: float,
    inlet_stream: FluidStream,
) -> Tuple[float, FluidStream]:
    """Calculate outlet pressure and outlet stream(-properties) from compressor stage

    Args:
        polytropic_efficiency: Allowed values (0, 1]
        polytropic_head_joule_per_kg: [J/kg]
        inlet_stream: Inlet fluid to compressor stage

    Returns:
        Outlet pressure
        Outlet fluid stream

    """

    outlet_pressure_this_stage_bara_based_on_inlet_z_and_kappa = calculate_outlet_pressure_campbell(
        kappa=inlet_stream.kappa,
        polytropic_efficiency=polytropic_efficiency,
        polytropic_head_fluid_Joule_per_kg=polytropic_head_joule_per_kg,
        molar_mass=inlet_stream.molar_mass_kg_per_mol,
        z_inlet=inlet_stream.z,
        inlet_temperature_K=inlet_stream.temperature_kelvin,
        inlet_pressure_bara=inlet_stream.pressure_bara,
    )

    outlet_stream_compressor_current_iteration = inlet_stream.set_new_pressure_and_enthalpy_change(
        new_pressure=outlet_pressure_this_stage_bara_based_on_inlet_z_and_kappa,
        enthalpy_change_joule_per_kg=polytropic_head_joule_per_kg / polytropic_efficiency,
    )

    outlet_pressure_this_stage_bara = outlet_pressure_this_stage_bara_based_on_inlet_z_and_kappa * 0.95
    converged = False
    i = 0
    max_iterations = 20
    while not converged and i < max_iterations:
        z_average = (inlet_stream.z + outlet_stream_compressor_current_iteration.z) / 2.0
        kappa_average = (inlet_stream.kappa + outlet_stream_compressor_current_iteration.kappa) / 2.0
        outlet_pressure_previous = outlet_pressure_this_stage_bara
        outlet_pressure_this_stage_bara = calculate_outlet_pressure_campbell(
            kappa=kappa_average,
            polytropic_efficiency=polytropic_efficiency,
            polytropic_head_fluid_Joule_per_kg=polytropic_head_joule_per_kg,
            molar_mass=inlet_stream.molar_mass_kg_per_mol,
            z_inlet=z_average,
            inlet_temperature_K=inlet_stream.temperature_kelvin,
            inlet_pressure_bara=inlet_stream.pressure_bara,
        )

        outlet_stream_compressor_current_iteration = inlet_stream.set_new_pressure_and_enthalpy_change(
            new_pressure=outlet_pressure_this_stage_bara,
            enthalpy_change_joule_per_kg=polytropic_head_joule_per_kg / polytropic_efficiency,
        )

        diff = abs(outlet_pressure_previous - outlet_pressure_this_stage_bara) / outlet_pressure_this_stage_bara

        converged = diff < OUTLET_PRESSURE_CONVERGENCE_TOLERANCE

        i += 1

        if i == max_iterations:
            logger.error(
                "calculate_outlet_pressure_and_stream"
                f" did not converge after {max_iterations} iterations."
                f" inlet_z: {inlet_stream.z}."
                f" inlet_kappa: {inlet_stream.kappa}."
                f" polytropic_efficiency: {polytropic_efficiency}."
                f" polytropic_head_joule_per_kg: {polytropic_head_joule_per_kg}."
                f" molar_mass_kg_per_mol: {inlet_stream.molar_mass_kg_per_mol}."
                f" inlet_temperature_kelvin: {inlet_stream.temperature_kelvin}."
                f" inlet_pressure_bara: {inlet_stream.pressure_bara}."
                f" Final diff between target and result was {diff}, while expected convergence diff criteria is set to diff lower than {OUTLET_PRESSURE_CONVERGENCE_TOLERANCE}"
                f" NOTE! We will use as the closest result we got for target for further calculations."
                " This should normally not happen. Please contact eCalc support."
            )

    return (
        outlet_pressure_this_stage_bara,
        outlet_stream_compressor_current_iteration,
    )
