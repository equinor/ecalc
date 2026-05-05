import math

from libecalc.common.errors.exceptions import IllegalStateException
from libecalc.common.logger import logger
from libecalc.common.numeric_methods import DampState, adaptive_pressure_update
from libecalc.common.units import UnitConstants
from libecalc.domain.process.compressor.core.train.utils.enthalpy_calculations import calculate_outlet_pressure_campbell
from libecalc.process.fluid_stream.fluid import Fluid
from libecalc.process.fluid_stream.fluid_properties import FluidProperties
from libecalc.process.fluid_stream.fluid_service import FluidService
from libecalc.process.fluid_stream.fluid_stream import FluidStream

FLOATING_POINT_PRECISION = 1e-6
EPSILON = 1e-5
PRESSURE_CALCULATION_TOLERANCE = 1e-3
POWER_CALCULATION_TOLERANCE = 1e-3
RATE_CALCULATION_TOLERANCE = 1e-3
RECIRCULATION_BOUNDARY_TOLERANCE = 1e-6
# -----------------------------------------------------------------------------
# Impossible pressure sanity cap.  Protects the PH flash when the first
# Campbell estimate is evaluated for an artificial max-speed head in edge cases.
# -----------------------------------------------------------------------------
MAX_FIRST_GUESS_BAR = 2_000.0  # [bara]
COMPRESSOR_PH_ENTHALPY_REL_TOLERANCE = 1e-4
COMPRESSOR_PH_ENTHALPY_ABS_TOLERANCE_JOULE_PER_KG = 10.0


class CompressorOutletCalculationError(IllegalStateException):
    """Raised when compressor outlet thermodynamics cannot produce a usable state."""


def _require_positive_finite(value: float, name: str, context: str) -> None:
    if not math.isfinite(value) or value <= 0:
        raise CompressorOutletCalculationError(f"{context}: expected finite positive {name}, got {value}.")


def _validate_compressor_ph_flash_result(
    properties: FluidProperties,
    target_pressure_bara: float,
    target_enthalpy_joule_per_kg: float,
    context: str,
) -> None:
    _require_positive_finite(properties.pressure_bara, "pressure_bara", context)
    _require_positive_finite(properties.temperature_kelvin, "temperature_kelvin", context)
    _require_positive_finite(properties.density, "density", context)
    _require_positive_finite(properties.z, "z", context)
    _require_positive_finite(properties.kappa, "kappa", context)
    _require_positive_finite(properties.standard_density, "standard_density", context)
    _require_positive_finite(target_pressure_bara, "target_pressure_bara", context)

    if (
        not math.isfinite(properties.vapor_fraction_molar)
        or not -EPSILON <= properties.vapor_fraction_molar <= 1 + EPSILON
    ):
        raise CompressorOutletCalculationError(
            f"{context}: expected finite vapor_fraction_molar in [0, 1], got {properties.vapor_fraction_molar}."
        )

    if not math.isfinite(target_enthalpy_joule_per_kg):
        raise CompressorOutletCalculationError(
            f"{context}: expected finite target_enthalpy_joule_per_kg, got {target_enthalpy_joule_per_kg}."
        )

    enthalpy_error = abs(properties.enthalpy_joule_per_kg - target_enthalpy_joule_per_kg)
    enthalpy_tolerance = max(
        COMPRESSOR_PH_ENTHALPY_ABS_TOLERANCE_JOULE_PER_KG,
        abs(target_enthalpy_joule_per_kg) * COMPRESSOR_PH_ENTHALPY_REL_TOLERANCE,
    )
    if not math.isfinite(properties.enthalpy_joule_per_kg) or enthalpy_error > enthalpy_tolerance:
        raise CompressorOutletCalculationError(
            f"{context}: PH flash did not satisfy target enthalpy. "
            f"target={target_enthalpy_joule_per_kg}, result={properties.enthalpy_joule_per_kg}, "
            f"error={enthalpy_error}, tolerance={enthalpy_tolerance}."
        )


def _flash_ph_for_compressor_outlet(
    fluid_service: FluidService,
    inlet_stream: FluidStream,
    outlet_pressure_bara: float,
    target_enthalpy: float,
    context: str,
) -> FluidProperties:
    try:
        return fluid_service.flash_ph(
            inlet_stream.fluid_model,
            outlet_pressure_bara,
            target_enthalpy,
            temperature_guess_kelvin=inlet_stream.temperature_kelvin,
        )
    except IllegalStateException as error:
        raise CompressorOutletCalculationError(f"{context}: PH flash failed.") from error


def calculate_asv_corrected_rate(
    minimum_actual_rate_m3_per_hour: float,
    actual_rate_m3_per_hour: float,
    density_kg_per_m3,
) -> tuple[float, float]:
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
    fluid_service: FluidService,
) -> FluidStream:
    """Calculate outlet pressure and outlet stream(-properties) from compressor stage

    Args:
        polytropic_efficiency: Allowed values (0, 1]
        polytropic_head_joule_per_kg: [J/kg]
        inlet_stream: Inlet fluid to compressor stage
        fluid_service: Service for performing flash operations

    Returns:
        Outlet fluid stream

    """

    # Initial guess for pressure outlet
    outlet_pressure_this_stage_bara_based_on_inlet_z_and_kappa = calculate_outlet_pressure_campbell(
        kappa=inlet_stream.kappa,
        polytropic_efficiency=polytropic_efficiency,
        polytropic_head_fluid_Joule_per_kg=polytropic_head_joule_per_kg,
        molar_mass=inlet_stream.molar_mass,
        z_inlet=inlet_stream.z,
        inlet_temperature_K=inlet_stream.temperature_kelvin,
        inlet_pressure_bara=inlet_stream.pressure_bara,
    )
    _require_positive_finite(
        outlet_pressure_this_stage_bara_based_on_inlet_z_and_kappa,
        "initial Campbell outlet pressure",
        "calculate_outlet_pressure_and_stream",
    )

    # Hard cap to protect the PH flash / EOS (primarily during non-physical max-speed probe)
    if outlet_pressure_this_stage_bara_based_on_inlet_z_and_kappa > MAX_FIRST_GUESS_BAR:
        logger.warning(
            "Campbell first guess %.0f bar discharge pressure exceeds cap of %.0f bar; "
            "capping to protect EOS (head %.0f J/kg, z_inlet: %.2f)."
            "This is a non-physical case, but may happen during max-speed probe in compressor solver",
            outlet_pressure_this_stage_bara_based_on_inlet_z_and_kappa,
            MAX_FIRST_GUESS_BAR,
            polytropic_head_joule_per_kg,
            inlet_stream.z,
        )
        outlet_pressure_this_stage_bara_based_on_inlet_z_and_kappa = MAX_FIRST_GUESS_BAR

    enthalpy_change = polytropic_head_joule_per_kg / polytropic_efficiency
    target_enthalpy = inlet_stream.enthalpy_joule_per_kg + enthalpy_change
    props = _flash_ph_for_compressor_outlet(
        fluid_service=fluid_service,
        inlet_stream=inlet_stream,
        outlet_pressure_bara=float(outlet_pressure_this_stage_bara_based_on_inlet_z_and_kappa),
        target_enthalpy=target_enthalpy,
        context="calculate_outlet_pressure_and_stream initial PH flash",
    )
    _validate_compressor_ph_flash_result(
        props,
        target_pressure_bara=float(outlet_pressure_this_stage_bara_based_on_inlet_z_and_kappa),
        target_enthalpy_joule_per_kg=target_enthalpy,
        context="calculate_outlet_pressure_and_stream initial PH flash",
    )
    outlet_fluid = Fluid(fluid_model=inlet_stream.fluid_model, properties=props)
    outlet_stream_compressor_current_iteration = inlet_stream.with_new_fluid(outlet_fluid)

    outlet_pressure_this_stage_bara = outlet_pressure_this_stage_bara_based_on_inlet_z_and_kappa * 0.95
    converged = False
    i = 0
    max_iterations = 30
    state = DampState()
    while not converged and i < max_iterations:
        z_average = (inlet_stream.z + outlet_stream_compressor_current_iteration.z) / 2.0
        kappa_average = (inlet_stream.kappa + outlet_stream_compressor_current_iteration.kappa) / 2.0
        outlet_pressure_previous = outlet_pressure_this_stage_bara
        p_raw = calculate_outlet_pressure_campbell(
            kappa=kappa_average,
            polytropic_efficiency=polytropic_efficiency,
            polytropic_head_fluid_Joule_per_kg=polytropic_head_joule_per_kg,
            molar_mass=inlet_stream.molar_mass,
            z_inlet=z_average,
            inlet_temperature_K=inlet_stream.temperature_kelvin,
            inlet_pressure_bara=inlet_stream.pressure_bara,
        )
        _require_positive_finite(
            p_raw,
            "Campbell outlet pressure",
            f"calculate_outlet_pressure_and_stream iteration {i}",
        )
        # Adaptive damping for cases where needed (non-invasive for normal cases)
        outlet_pressure_this_stage_bara, state = adaptive_pressure_update(
            p_prev=outlet_pressure_this_stage_bara,
            p_raw=p_raw,
            state=state,
        )
        _require_positive_finite(
            outlet_pressure_this_stage_bara,
            "damped outlet pressure",
            f"calculate_outlet_pressure_and_stream iteration {i}",
        )

        props = _flash_ph_for_compressor_outlet(
            fluid_service=fluid_service,
            inlet_stream=inlet_stream,
            outlet_pressure_bara=outlet_pressure_this_stage_bara,
            target_enthalpy=target_enthalpy,
            context=f"calculate_outlet_pressure_and_stream iteration {i} PH flash",
        )
        _validate_compressor_ph_flash_result(
            props,
            target_pressure_bara=outlet_pressure_this_stage_bara,
            target_enthalpy_joule_per_kg=target_enthalpy,
            context=f"calculate_outlet_pressure_and_stream iteration {i} PH flash",
        )
        outlet_fluid = Fluid(fluid_model=inlet_stream.fluid_model, properties=props)
        outlet_stream_compressor_current_iteration = inlet_stream.with_new_fluid(outlet_fluid)

        diff = abs(outlet_pressure_previous - outlet_pressure_this_stage_bara) / outlet_pressure_this_stage_bara

        converged = diff < PRESSURE_CALCULATION_TOLERANCE

        i += 1

        if i == max_iterations:
            logger.error(
                "calculate_outlet_pressure_and_stream"
                f" did not converge after {max_iterations} iterations."
                f" inlet_z: {inlet_stream.z}."
                f" inlet_kappa: {inlet_stream.kappa}."
                f" polytropic_efficiency: {polytropic_efficiency}."
                f" polytropic_head_joule_per_kg: {polytropic_head_joule_per_kg}."
                f" molar_mass_kg_per_mol: {inlet_stream.molar_mass}."
                f" inlet_temperature_kelvin: {inlet_stream.temperature_kelvin}."
                f" inlet_pressure_bara: {inlet_stream.pressure_bara}."
                f" Final diff between target and result was {diff}, while expected convergence diff criteria is set to diff lower than {PRESSURE_CALCULATION_TOLERANCE}"
                f" NOTE! We will use as the closest result we got for target for further calculations."
                " This should normally not happen. Please contact eCalc support."
            )

    return outlet_stream_compressor_current_iteration
