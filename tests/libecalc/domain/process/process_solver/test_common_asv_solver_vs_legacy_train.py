import pytest
from inline_snapshot import snapshot

from libecalc.common.fixed_speed_pressure_control import FixedSpeedPressureControl
from libecalc.domain.process.compressor.core.results import CompressorTrainResultSingleTimeStep
from libecalc.domain.process.compressor.core.train.train_evaluation_input import CompressorTrainEvaluationInput
from libecalc.domain.process.entities.shaft import VariableSpeedShaft
from libecalc.domain.process.process_solver.float_constraint import FloatConstraint
from libecalc.domain.process.process_solver.solvers.recirculation_solver import RecirculationConfiguration
from libecalc.domain.process.value_objects.chart import ChartCurve
from libecalc.domain.process.value_objects.fluid_stream import FluidModel, FluidService


def make_variable_speed_chart_data(chart_data_factory, *, min_rate, max_rate, head_hi, head_lo, eff):
    """
    Two speed curves with identical envelope (min/max rate).
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


def test_common_asv_solver_vs_legacy_train(
    variable_speed_compressor_train,
    compressor_stage_factory,
    compressor_stages,
    fluid_service,
    variable_speed_compressor_chart_data,
    chart_data_factory,
    stream_factory,
    stage_units_factory,
    with_common_asv,
    process_runner_factory,
    common_asv_anti_surge_strategy_factory,
    common_asv_pressure_control_strategy_factory,
    outlet_pressure_solver_factory,
):
    temperature = 300.0
    target_pressure = 92.0

    inlet_stream = stream_factory(standard_rate_m3_per_day=500000.0, pressure_bara=30.0, temperature_kelvin=temperature)
    # assert inlet_stream.volumetric_rate_m3_per_hour == snapshot(681.2529349883239)

    # Use the inlet actual volumetric rate to define a stage-1 minimum flow that is guaranteed
    # to be above the operating point when recirculation=0.
    q0 = float(inlet_stream.volumetric_rate_m3_per_hour)
    stage1_min_rate = q0 * 1.5
    stage1_max_rate = q0 * 10.0

    # Stage 1 is configured to be below minimum flow at recirculation=0 by setting min_rate > q0.
    # Max rate is set sufficiently high so that a feasible point exists after adding recirculation.
    stage1_chart_data = make_variable_speed_chart_data(
        chart_data_factory,
        min_rate=stage1_min_rate,
        max_rate=stage1_max_rate,
        head_hi=80000.0,
        head_lo=40000.0,
        eff=0.75,
    )

    # Stage 2 should not be the limiting stage in this test; it is given a wide envelope.
    stage2_chart_data = make_variable_speed_chart_data(
        chart_data_factory,
        min_rate=0.0,
        max_rate=stage1_max_rate * 2.0,
        head_hi=60000.0,
        head_lo=30000.0,
        eff=0.72,
    )

    # Evaluate old legacy train.
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

    stages_old = [stage1_old, stage2_old]

    train_old = variable_speed_compressor_train(
        stages=stages_old, shaft=shaft_old, pressure_control=FixedSpeedPressureControl.INDIVIDUAL_ASV_PRESSURE
    )
    train_old._fluid_model = [inlet_stream.fluid_model]

    evaluation_input_old = CompressorTrainEvaluationInput(
        suction_pressure=inlet_stream.pressure_bara,
        discharge_pressure=target_pressure,
        rates=[inlet_stream.standard_rate_sm3_per_day],
    )
    old_result = train_old.evaluate_given_constraints(evaluation_input_old)
    old_outlet_stream = old_result.outlet_stream

    # Evaluate new train solver.
    shaft_new = VariableSpeedShaft()
    stage1_new = stage_units_factory(chart_data=stage1_chart_data, shaft=shaft_new, temperature_kelvin=temperature)
    stage2_new = stage_units_factory(chart_data=stage2_chart_data, shaft=shaft_new, temperature_kelvin=temperature)

    common_asv, loop_id, first_compressor = with_common_asv([*stage1_new, *stage2_new])

    runner = process_runner_factory(units=[common_asv], shaft=shaft_new)
    anti_surge_strategy = common_asv_anti_surge_strategy_factory(
        runner=runner,
        recirculation_loop_id=loop_id,
        first_compressor=first_compressor,
    )
    pressure_control_strategy = common_asv_pressure_control_strategy_factory(
        runner=runner,
        recirculation_loop_id=loop_id,
        first_compressor=first_compressor,
    )
    train_solver = outlet_pressure_solver_factory(
        shaft=shaft_new,
        runner=runner,
        anti_surge_strategy=anti_surge_strategy,
        pressure_control_strategy=pressure_control_strategy,
    )
    solution = train_solver.find_solution(
        pressure_constraint=FloatConstraint(target_pressure),
        inlet_stream=inlet_stream,
    )
    runner.apply_configurations(solution.configuration)
    new_outlet_stream = runner.run(inlet_stream=inlet_stream)

    assert new_outlet_stream.volumetric_rate_m3_per_hour == pytest.approx(
        old_outlet_stream.volumetric_rate_m3_per_hour, rel=0.001
    )  # 0.1 %
    assert new_outlet_stream.pressure_bara == pytest.approx(
        old_outlet_stream.pressure_bara, rel=0.00000001
    )  # 0.000001 %
    assert new_outlet_stream.density == pytest.approx(old_outlet_stream.density, rel=0.001)  # 0.1 %
    assert shaft_new.get_speed() > shaft_old.get_speed()  # only recirc in one compressor in old result

    # For now new and old recirculation rate is not expected to match - as the old train recirculates individual stages and finds a solution
    # without common asv
    recirculation_configuration = [
        config for config in solution.configuration if isinstance(config.value, RecirculationConfiguration)
    ][0]
    new_recirculation_rate = recirculation_configuration.value.recirculation_rate
    old_recirculation_rate_1 = (
        old_result.stage_results[0].standard_rate_asv_corrected_sm3_per_day
        - old_result.stage_results[0].standard_rate_sm3_per_day
    )
    old_recirculation_rate_2 = (
        old_result.stage_results[1].standard_rate_asv_corrected_sm3_per_day
        - old_result.stage_results[1].standard_rate_sm3_per_day
    )

    assert new_recirculation_rate == snapshot(250000.000001)
    assert old_recirculation_rate_1 == snapshot(249999.99999999988)
    assert old_recirculation_rate_2 == 0.0
