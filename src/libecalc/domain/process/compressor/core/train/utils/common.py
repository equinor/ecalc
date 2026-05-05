import math

from libecalc.common.errors.exceptions import IllegalStateException
from libecalc.common.logger import logger
from libecalc.common.numeric_methods import DampState, adaptive_pressure_update, find_root
from libecalc.common.units import UnitConstants
from libecalc.domain.process.compressor.core.train.utils.enthalpy_calculations import calculate_outlet_pressure_campbell
from libecalc.process.fluid_stream.fluid import Fluid
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
# Campbell estimate is evaluated for an artificial max‑speed head in edge cases.
# -----------------------------------------------------------------------------
MAX_FIRST_GUESS_BAR = 2_000.0  # [bara]


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
    """Calculate outlet pressure and outlet stream(-properties) from compressor stage.

    Tries the legacy PH-flash fixed-point loop first; falls back to a more robust
    TP-flash bracket+bisect on outlet pressure if the PH-flash loop refuses
    (e.g. NeqSim PHflash IsNaNException on dense supercritical inputs).

    Args:
        polytropic_efficiency: Allowed values (0, 1]
        polytropic_head_joule_per_kg: [J/kg]
        inlet_stream: Inlet fluid to compressor stage
        fluid_service: Service for performing flash operations

    Returns:
        Outlet fluid stream
    """
    try:
        return _calculate_outlet_pressure_via_ph_flash_loop(
            polytropic_efficiency=polytropic_efficiency,
            polytropic_head_joule_per_kg=polytropic_head_joule_per_kg,
            inlet_stream=inlet_stream,
            fluid_service=fluid_service,
        )
    except IllegalStateException as ph_loop_exc:
        logger.info(
            "PH-flash outlet-pressure loop refused (%s). Falling back to TP-flash bracket+bisect on outlet pressure.",
            ph_loop_exc,
        )
        return _calculate_outlet_pressure_via_tp_bracket_bisect(
            polytropic_efficiency=polytropic_efficiency,
            polytropic_head_joule_per_kg=polytropic_head_joule_per_kg,
            inlet_stream=inlet_stream,
            fluid_service=fluid_service,
        )


def _calculate_outlet_pressure_via_ph_flash_loop(
    polytropic_efficiency: float,
    polytropic_head_joule_per_kg: float,
    inlet_stream: FluidStream,
    fluid_service: FluidService,
) -> FluidStream:
    """Legacy PH-flash fixed-point iteration on outlet pressure.

    Raises ``IllegalStateException`` for inputs the EOS can't handle so the
    caller can fall back to a more robust solver.
    """

    outlet_pressure_this_stage_bara_based_on_inlet_z_and_kappa = calculate_outlet_pressure_campbell(
        kappa=inlet_stream.kappa,
        polytropic_efficiency=polytropic_efficiency,
        polytropic_head_fluid_Joule_per_kg=polytropic_head_joule_per_kg,
        molar_mass=inlet_stream.molar_mass,
        z_inlet=inlet_stream.z,
        inlet_temperature_K=inlet_stream.temperature_kelvin,
        inlet_pressure_bara=inlet_stream.pressure_bara,
    )

    if not math.isfinite(outlet_pressure_this_stage_bara_based_on_inlet_z_and_kappa):
        raise IllegalStateException(
            "Refusing to call NeqSim PH flash with non-finite outlet pressure "
            f"{outlet_pressure_this_stage_bara_based_on_inlet_z_and_kappa} bara "
            f"(polytropic_head={polytropic_head_joule_per_kg} J/kg, z_inlet={inlet_stream.z}, "
            f"kappa={inlet_stream.kappa})."
        )

    if outlet_pressure_this_stage_bara_based_on_inlet_z_and_kappa > MAX_FIRST_GUESS_BAR:
        outlet_pressure_this_stage_bara_based_on_inlet_z_and_kappa = MAX_FIRST_GUESS_BAR

    enthalpy_change = polytropic_head_joule_per_kg / polytropic_efficiency
    target_enthalpy = inlet_stream.enthalpy_joule_per_kg + enthalpy_change
    if not math.isfinite(target_enthalpy):
        raise IllegalStateException(
            "Refusing to call NeqSim PH flash with non-finite target enthalpy "
            f"{target_enthalpy} J/kg (inlet_h={inlet_stream.enthalpy_joule_per_kg} J/kg, "
            f"polytropic_head={polytropic_head_joule_per_kg} J/kg, "
            f"polytropic_efficiency={polytropic_efficiency})."
        )

    props = fluid_service.flash_ph(
        inlet_stream.fluid_model,
        float(outlet_pressure_this_stage_bara_based_on_inlet_z_and_kappa),
        target_enthalpy,
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
        if not math.isfinite(p_raw):
            raise IllegalStateException(
                f"Refusing non-finite Campbell outlet pressure {p_raw} during PH iteration "
                f"(z_avg={z_average}, kappa_avg={kappa_average})."
            )
        if p_raw > MAX_FIRST_GUESS_BAR:
            p_raw = MAX_FIRST_GUESS_BAR
        # Adaptive damping for cases where needed (non-invasive for normal cases)
        outlet_pressure_this_stage_bara, state = adaptive_pressure_update(
            p_prev=outlet_pressure_this_stage_bara,
            p_raw=p_raw,
            state=state,
        )

        props = fluid_service.flash_ph(
            inlet_stream.fluid_model,
            outlet_pressure_this_stage_bara,
            target_enthalpy,
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


def _calculate_outlet_pressure_via_tp_bracket_bisect(
    polytropic_efficiency: float,
    polytropic_head_joule_per_kg: float,
    inlet_stream: FluidStream,
    fluid_service: FluidService,
) -> FluidStream:
    """Robust fallback: bracket+bisect on outlet pressure with TP-flashes.

    For a candidate ``P_out``, estimate ``T_out`` via the polytropic ideal-gas
    relation ``T_out = T_in (P_out/P_in)^((κ-1)/κ)``, TP-flash there (much more
    stable than PH-flash since P,T uniquely fix the EoS state), then solve

        f(P_out) = Campbell(avg z, avg κ) - P_out = 0

    for ``P_out`` with Brent's method on ``[inlet_p, MAX_FIRST_GUESS_BAR]``.
    Finally, do a single PH-flash at ``P*`` for the true outlet fluid state.
    """
    enthalpy_change = polytropic_head_joule_per_kg / polytropic_efficiency
    target_enthalpy = inlet_stream.enthalpy_joule_per_kg + enthalpy_change

    if not math.isfinite(target_enthalpy):
        raise IllegalStateException(
            f"Non-finite target enthalpy {target_enthalpy} J/kg "
            f"(inlet_h={inlet_stream.enthalpy_joule_per_kg}, "
            f"head={polytropic_head_joule_per_kg}, eta={polytropic_efficiency})."
        )

    inlet_p = inlet_stream.pressure_bara
    inlet_t = inlet_stream.temperature_kelvin
    inlet_z = inlet_stream.z
    inlet_k = inlet_stream.kappa
    molar_mass = inlet_stream.molar_mass

    def _campbell(z_avg: float, k_avg: float) -> float:
        return calculate_outlet_pressure_campbell(
            kappa=k_avg,
            polytropic_efficiency=polytropic_efficiency,
            polytropic_head_fluid_Joule_per_kg=polytropic_head_joule_per_kg,
            molar_mass=molar_mass,
            z_inlet=z_avg,
            inlet_temperature_K=inlet_t,
            inlet_pressure_bara=inlet_p,
        )

    def _residual(p_out_bara: float) -> float:
        t_out_guess = inlet_t * (p_out_bara / inlet_p) ** ((inlet_k - 1.0) / inlet_k)
        props = fluid_service.flash_pt(inlet_stream.fluid_model, p_out_bara, t_out_guess)
        z_avg = 0.5 * (inlet_z + props.z)
        k_avg = 0.5 * (inlet_k + props.kappa)
        p_predicted = _campbell(z_avg, k_avg)
        if not math.isfinite(p_predicted):
            raise IllegalStateException(
                f"Non-finite Campbell prediction at P_out={p_out_bara}: z_avg={z_avg}, kappa_avg={k_avg}."
            )
        if p_predicted > MAX_FIRST_GUESS_BAR:
            p_predicted = MAX_FIRST_GUESS_BAR
        return p_predicted - p_out_bara

    p_low = inlet_p * (1.0 + EPSILON)
    p_high = MAX_FIRST_GUESS_BAR

    f_low = _residual(p_low)
    f_high = _residual(p_high)

    if f_low * f_high > 0:
        raise IllegalStateException(
            f"No bracket for outlet pressure root in [{p_low:.2f}, {p_high:.2f}] bara: "
            f"f_low={f_low:.2e}, f_high={f_high:.2e}. Likely the chart head "
            f"({polytropic_head_joule_per_kg:.0f} J/kg) is being extrapolated outside "
            "its valid envelope."
        )

    p_star = find_root(
        lower_bound=p_low,
        upper_bound=p_high,
        func=_residual,
        relative_convergence_tolerance=PRESSURE_CALCULATION_TOLERANCE,
        maximum_number_of_iterations=30,
    )

    props = fluid_service.flash_ph(inlet_stream.fluid_model, p_star, target_enthalpy)
    outlet_fluid = Fluid(fluid_model=inlet_stream.fluid_model, properties=props)
    return inlet_stream.with_new_fluid(outlet_fluid)
