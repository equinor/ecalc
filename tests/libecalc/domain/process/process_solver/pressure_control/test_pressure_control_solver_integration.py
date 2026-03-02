import pytest
from inline_snapshot import snapshot

from libecalc.common.fixed_speed_pressure_control import FixedSpeedPressureControl
from libecalc.domain.process.compressor.core.results import CompressorTrainResultSingleTimeStep
from libecalc.domain.process.compressor.core.train.train_evaluation_input import CompressorTrainEvaluationInput
from libecalc.domain.process.entities.process_units.recirculation_loop import RecirculationLoop
from libecalc.domain.process.entities.shaft import VariableSpeedShaft
from libecalc.domain.process.process_solver.boundary import Boundary
from libecalc.domain.process.process_solver.float_constraint import FloatConstraint
from libecalc.domain.process.process_solver.pressure_control.factories import (
    create_capacity_policy,
    create_pressure_control_policy,
)
from libecalc.domain.process.process_solver.pressure_control.solver import PressureControlSolver
from libecalc.domain.process.process_solver.pressure_control.types import PressureControlConfiguration
from libecalc.domain.process.process_solver.search_strategies import BinarySearchStrategy, ScipyRootFindingStrategy
from libecalc.domain.process.process_system.process_system import ProcessSystem
from libecalc.domain.process.value_objects.chart import ChartCurve
from libecalc.domain.process.value_objects.fluid_stream import FluidModel, FluidService


def make_variable_speed_chart_data(chart_data_factory, *, min_rate, max_rate, head_hi, head_lo, eff):
    """
    Two speed curves with identical envelope (min/max rate).
    Kept in-sync with test_common_asv_solver_vs_legacy_train.
    """
    curves = [
        ChartCurve(
            speed_rpm=75.0,
            rate_actual_m3_hour=[min_rate, max_rate],
            polytropic_head_joule_per_kg=[head_hi, head_lo],
            efficiency_fraction=[eff, eff],
        ),
        ChartCurve(
            speed_rpm=105.0,
            rate_actual_m3_hour=[min_rate, max_rate],
            polytropic_head_joule_per_kg=[head_hi * 1.05, head_lo * 1.05],  # Slightly higher at higher speed
            efficiency_fraction=[eff, eff],
        ),
    ]
    return chart_data_factory.from_curves(curves=curves, control_margin=0.0)


def _calc_recirculation_rate_from_loss_mw(
    fluid_service: FluidService, fluid_model: FluidModel, result: CompressorTrainResultSingleTimeStep
):
    kilo_joule_per_hour_to_mw_factor = 1 / (60 * 60 * 1000)
    enthalpy_change = result.polytropic_enthalpy_change_kilo_joule_per_kg
    mass_rate = result.mass_rate_kg_per_hour
    recirculation_loss_mw = result.asv_recirculation_loss_mw
    mass_rate_corrected = (recirculation_loss_mw / (enthalpy_change * kilo_joule_per_hour_to_mw_factor)) + mass_rate
    recirculation_mass_rate = mass_rate_corrected - mass_rate
    recirculation_rate = fluid_service.mass_rate_to_standard_rate(
        mass_rate_kg_per_h=recirculation_mass_rate, fluid_model=fluid_model
    )
    return recirculation_rate


def test_pressure_control_solver_common_asv_capacity_then_pressure_control(
    chart_data_factory,
    compressor_train_stage_process_unit_factory,
    stream_factory,
    fluid_service,
):
    temperature = 300.0
    target_pressure = FloatConstraint(92.0, abs_tol=1e-2)

    inlet_stream = stream_factory(
        standard_rate_m3_per_day=500_000.0,
        pressure_bara=30.0,
        temperature_kelvin=temperature,
    )

    # Make the relationship between inlet stream and chart min-rate explicit.
    q0 = float(inlet_stream.volumetric_rate_m3_per_hour)
    stage1_min_rate = q0 * 1.5  # guarantees RateTooLow when recirc=0
    stage1_max_rate = q0 * 10.0

    stage1_chart_data = make_variable_speed_chart_data(
        chart_data_factory,
        min_rate=stage1_min_rate,
        max_rate=stage1_max_rate,
        head_hi=80_000.0,
        head_lo=40_000.0,
        eff=0.75,
    )
    stage2_chart_data = make_variable_speed_chart_data(
        chart_data_factory,
        min_rate=0.0,
        max_rate=stage1_max_rate * 2.0,
        head_hi=60_000.0,
        head_lo=30_000.0,
        eff=0.72,
    )

    shaft = VariableSpeedShaft()

    stage1 = compressor_train_stage_process_unit_factory(
        chart_data=stage1_chart_data,
        shaft=shaft,
        temperature_kelvin=temperature,
    )
    stage2 = compressor_train_stage_process_unit_factory(
        chart_data=stage2_chart_data,
        shaft=shaft,
        temperature_kelvin=temperature,
    )

    compressor_train = ProcessSystem(process_units=[stage1, stage2])
    recirculation_loop = RecirculationLoop(inner_process=compressor_train, fluid_service=fluid_service)

    speed_boundary = Boundary(min=75.0, max=105.0)

    # Recirculation boundary based on stage-1 maximum capacity (same idea as CommonASVSolver).
    max_std_rate_stage1 = stage1.get_maximum_standard_rate(inlet_stream=inlet_stream)
    max_recirculation_rate = max(0.0, max_std_rate_stage1 - inlet_stream.standard_rate_sm3_per_day)
    recirc_boundary = Boundary(min=0.0, max=max_recirculation_rate * (1 - 1e-12))

    search_strategy = BinarySearchStrategy(tolerance=1e-2)
    root_finding_strategy = ScipyRootFindingStrategy(tolerance=1e-5)

    capacity_policy = create_capacity_policy(
        "COMMON_ASV_MIN_FLOW",
        recirculation_rate_boundary=recirc_boundary,
        search_strategy=search_strategy,
        root_finding_strategy=root_finding_strategy,
    )
    pressure_policy = create_pressure_control_policy(
        "COMMON_ASV",
        recirculation_rate_boundary=recirc_boundary,
        upstream_delta_pressure_boundary=Boundary(min=0.0, max=0.0),  # unused in this test
        root_finding_strategy=root_finding_strategy,
        search_strategy=search_strategy,
    )

    solver = PressureControlSolver(
        speed_boundary=speed_boundary,
        search_strategy=search_strategy,
        root_finding_strategy=root_finding_strategy,
        capacity_policy=capacity_policy,
        pressure_control_policy=pressure_policy,
    )

    def evaluate_system(cfg: PressureControlConfiguration):
        shaft.set_speed(cfg.speed)
        recirculation_loop.set_recirculation_rate(cfg.recirculation_rate)
        return recirculation_loop.propagate_stream(inlet_stream=inlet_stream)

    solution = solver.solve(
        target_pressure=target_pressure,
        evaluate_system=evaluate_system,
    )

    assert solution.success is True

    # Capacity policy should enforce recirculation > 0 due to stage-1 min flow.
    assert solution.configuration.recirculation_rate > 0.0

    outlet = evaluate_system(solution.configuration)
    assert float(outlet.pressure_bara) == pytest.approx(target_pressure.value, abs=target_pressure.abs_tol)

    assert speed_boundary.min <= solution.configuration.speed <= speed_boundary.max
    assert solution.configuration.recirculation_rate >= 0.0


def test_pressure_control_solver_common_asv_vs_legacy_train(
    variable_speed_compressor_train,
    compressor_stage_factory,
    fluid_service,
    chart_data_factory,
    stream_factory,
    compressor_train_stage_process_unit_factory,
):
    """
    Integration-style regression test.

    Compares PressureControlSolver (COMMON_ASV policies) against the legacy compressor train implementation
    (INDIVIDUAL_ASV_PRESSURE) for a 2-stage variable-speed train. We assert that the new solver produces
    a similar outlet stream and approximately similar shaft speed.

    Note: recirculation rate is not expected to match legacy, since legacy recirculates per-stage while the new
    implementation uses a common recirculation loop.
    """
    temperature = 300.0
    target_pressure = 92.0

    inlet_stream = stream_factory(
        standard_rate_m3_per_day=500_000.0,
        pressure_bara=30.0,
        temperature_kelvin=temperature,
    )

    # Define stage-1 min flow above operating point for recirc=0.
    q0 = float(inlet_stream.volumetric_rate_m3_per_hour)
    stage1_min_rate = q0 * 1.5
    stage1_max_rate = q0 * 10.0

    stage1_chart_data = make_variable_speed_chart_data(
        chart_data_factory,
        min_rate=stage1_min_rate,
        max_rate=stage1_max_rate,
        head_hi=80_000.0,
        head_lo=40_000.0,
        eff=0.75,
    )
    stage2_chart_data = make_variable_speed_chart_data(
        chart_data_factory,
        min_rate=0.0,
        max_rate=stage1_max_rate * 2.0,
        head_hi=60_000.0,
        head_lo=30_000.0,
        eff=0.72,
    )

    # --- Legacy baseline (old train) ---
    shaft_old = VariableSpeedShaft()
    stage1_old = compressor_stage_factory(
        compressor_chart_data=stage1_chart_data,
        shaft=shaft_old,
        inlet_temperature_kelvin=temperature,
    )
    stage2_old = compressor_stage_factory(
        compressor_chart_data=stage2_chart_data,
        shaft=shaft_old,
        inlet_temperature_kelvin=temperature,
    )

    train_old = variable_speed_compressor_train(
        stages=[stage1_old, stage2_old],
        shaft=shaft_old,
        pressure_control=FixedSpeedPressureControl.INDIVIDUAL_ASV_PRESSURE,
    )
    train_old._fluid_model = [inlet_stream.fluid_model]

    evaluation_input_old = CompressorTrainEvaluationInput(
        suction_pressure=inlet_stream.pressure_bara,
        discharge_pressure=target_pressure,
        rates=[inlet_stream.standard_rate_sm3_per_day],
    )
    old_result = train_old.evaluate_given_constraints(evaluation_input_old)
    old_outlet_stream = old_result.outlet_stream

    # --- New approach (PressureControlSolver + policies) ---
    shaft_new = VariableSpeedShaft()
    stage1_new = compressor_train_stage_process_unit_factory(
        chart_data=stage1_chart_data,
        shaft=shaft_new,
        temperature_kelvin=temperature,
    )
    stage2_new = compressor_train_stage_process_unit_factory(
        chart_data=stage2_chart_data,
        shaft=shaft_new,
        temperature_kelvin=temperature,
    )

    compressor_train = ProcessSystem(process_units=[stage1_new, stage2_new])
    recirculation_loop = RecirculationLoop(inner_process=compressor_train, fluid_service=fluid_service)

    speed_boundary = Boundary(min=75.0, max=105.0)

    # Recirculation boundary based on stage-1 maximum capacity (same idea as CommonASVSolver).
    max_std_rate_stage1 = stage1_new.get_maximum_standard_rate(inlet_stream=inlet_stream)
    max_recirculation_rate = max(0.0, max_std_rate_stage1 - inlet_stream.standard_rate_sm3_per_day)
    recirc_boundary = Boundary(min=0.0, max=max_recirculation_rate * (1 - 1e-12))

    search_strategy = BinarySearchStrategy(tolerance=1e-2)
    root_finding_strategy = ScipyRootFindingStrategy(tolerance=1e-5)

    capacity_policy = create_capacity_policy(
        "COMMON_ASV_MIN_FLOW",
        recirculation_rate_boundary=recirc_boundary,
        search_strategy=search_strategy,
        root_finding_strategy=root_finding_strategy,
    )
    pressure_policy = create_pressure_control_policy(
        "COMMON_ASV",
        recirculation_rate_boundary=recirc_boundary,
        upstream_delta_pressure_boundary=Boundary(min=0.0, max=0.0),  # unused here
        root_finding_strategy=root_finding_strategy,
        search_strategy=search_strategy,
    )

    pressure_control_solver = PressureControlSolver(
        speed_boundary=speed_boundary,
        search_strategy=search_strategy,
        root_finding_strategy=root_finding_strategy,
        capacity_policy=capacity_policy,
        pressure_control_policy=pressure_policy,
    )

    def evaluate_system(cfg: PressureControlConfiguration):
        shaft_new.set_speed(cfg.speed)
        recirculation_loop.set_recirculation_rate(cfg.recirculation_rate)
        return recirculation_loop.propagate_stream(inlet_stream=inlet_stream)

    new_solution = pressure_control_solver.solve(
        target_pressure=FloatConstraint(target_pressure, abs_tol=1e-2),
        evaluate_system=evaluate_system,
    )
    assert new_solution.success is True

    new_outlet_stream = evaluate_system(new_solution.configuration)

    # --- Compare new vs legacy ---
    assert new_outlet_stream.volumetric_rate_m3_per_hour == pytest.approx(
        old_outlet_stream.volumetric_rate_m3_per_hour, rel=0.001
    )  # 0.1 %
    assert new_outlet_stream.pressure_bara == pytest.approx(old_outlet_stream.pressure_bara, rel=0.0000001)  # 0.00001 %
    assert new_outlet_stream.density == pytest.approx(old_outlet_stream.density, rel=0.001)  # 0.1 %
    assert shaft_new.get_speed() == pytest.approx(shaft_old.get_speed(), rel=0.032)  # 3.2 %

    # Recirculation rate: keep the snapshots, but don't require "new == old".
    new_recirculation_rate = new_solution.configuration.recirculation_rate
    old_recirculation_rate = _calc_recirculation_rate_from_loss_mw(
        fluid_service=fluid_service,
        result=old_result,
        fluid_model=old_outlet_stream.fluid_model,
    )

    assert new_recirculation_rate == snapshot(250213.62304662477)
    assert old_recirculation_rate == snapshot(141127.6427142186)
