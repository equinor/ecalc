import pytest

from libecalc.common.fixed_speed_pressure_control import FixedSpeedPressureControl
from libecalc.domain.process.compressor.core.train.train_evaluation_input import CompressorTrainEvaluationInput
from libecalc.domain.process.entities.shaft import VariableSpeedShaft
from libecalc.domain.process.process_solver.configuration import Configuration
from libecalc.domain.process.process_solver.float_constraint import FloatConstraint
from libecalc.domain.process.process_solver.solvers.recirculation_solver import RecirculationConfiguration
from libecalc.domain.process.process_solver.solvers.speed_solver import SpeedConfiguration
from libecalc.domain.process.value_objects.chart import ChartCurve


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


@pytest.mark.parametrize("pd_target", [50.0, 92.0, 150.0])
def test_individual_asv_rate_solver_vs_legacy_train(
    pd_target,
    variable_speed_compressor_train,
    compressor_stage_factory,
    compressor_stages,
    fluid_service,
    variable_speed_compressor_chart_data,
    chart_data_factory,
    stream_factory,
    compressor_factory,
    stage_units_factory,
    with_individual_asv,
    process_runner_factory,
    individual_asv_anti_surge_strategy_factory,
    individual_asv_rate_control_strategy_factory,
    outlet_pressure_solver_factory,
):
    temperature = 300.0
    target_pressure = pd_target

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
        stages=stages_old, shaft=shaft_old, pressure_control=FixedSpeedPressureControl.INDIVIDUAL_ASV_RATE
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
    compressor1 = compressor_factory(chart_data=stage1_chart_data)
    compressor2 = compressor_factory(chart_data=stage2_chart_data)
    stage1_new = stage_units_factory(compressor=compressor1, shaft=shaft_new, temperature_kelvin=temperature)
    stage2_new = stage_units_factory(compressor=compressor2, shaft=shaft_new, temperature_kelvin=temperature)

    compressors = [compressor1, compressor2]
    units_new, loops = with_individual_asv([*stage1_new, *stage2_new])
    recirculation_loop_ids = [loop.get_id() for loop in loops]

    runner = process_runner_factory(units=units_new, configuration_handlers=[shaft_new, *loops])
    anti_surge_strategy = individual_asv_anti_surge_strategy_factory(
        runner=runner,
        recirculation_loop_ids=recirculation_loop_ids,
        compressors=compressors,
    )
    pressure_control_strategy = individual_asv_rate_control_strategy_factory(
        runner=runner,
        recirculation_loop_ids=recirculation_loop_ids,
        compressors=compressors,
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
    config_dict = {config.simulation_unit_id: config for config in solution.configuration}
    speed_configuration = config_dict[shaft_new.get_id()].value
    runner.apply_configurations(solution.configuration)
    new_outlet_stream = runner.run(inlet_stream=inlet_stream)

    assert new_outlet_stream.volumetric_rate_m3_per_hour == pytest.approx(
        old_outlet_stream.volumetric_rate_m3_per_hour, rel=0.001
    )  # 0.1 %
    assert new_outlet_stream.pressure_bara == pytest.approx(old_outlet_stream.pressure_bara, rel=0.001)  # 0.000001 %
    assert new_outlet_stream.density == pytest.approx(old_outlet_stream.density, rel=0.001)  # 0.1 %
    assert speed_configuration.speed == pytest.approx(shaft_old.get_speed(), rel=0.001)  # 2.1 %

    # For now new and old recirculation rate is not expected to match - as the old train recirculates individual stages and finds a solution
    # without common asv
    new_recirculation_rates = [
        config.value.recirculation_rate
        for config in solution.configuration
        if isinstance(config.value, RecirculationConfiguration)
    ]
    old_recirculation_rates = [
        stage_result.inlet_stream_including_asv.standard_rate_sm3_per_day
        - stage_result.inlet_stream.standard_rate_sm3_per_day
        for stage_result in old_result.stage_results
    ]

    assert new_recirculation_rates == pytest.approx(old_recirculation_rates, rel=0.01)


@pytest.mark.parametrize("pd_target", [45.0, 92.0, 150.0])
def test_individual_asv_pressure_solver_vs_legacy_train(
    pd_target,
    variable_speed_compressor_train,
    compressor_stage_factory,
    compressor_stages,
    fluid_service,
    variable_speed_compressor_chart_data,
    chart_data_factory,
    stream_factory,
    compressor_factory,
    stage_units_factory,
    with_individual_asv,
    process_runner_factory,
    individual_asv_anti_surge_strategy_factory,
    individual_asv_pressure_control_strategy_factory,
    outlet_pressure_solver_factory,
):
    temperature = 300.0
    target_pressure = pd_target

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
    compressor1 = compressor_factory(chart_data=stage1_chart_data)
    compressor2 = compressor_factory(chart_data=stage2_chart_data)
    stage1_new = stage_units_factory(compressor=compressor1, shaft=shaft_new, temperature_kelvin=temperature)
    stage2_new = stage_units_factory(compressor=compressor2, shaft=shaft_new, temperature_kelvin=temperature)

    compressors = [compressor1, compressor2]
    units_new, loops = with_individual_asv([*stage1_new, *stage2_new])
    recirculation_loop_ids = [loop.get_id() for loop in loops]

    runner = process_runner_factory(units=units_new, configuration_handlers=[shaft_new, *loops])
    anti_surge_strategy = individual_asv_anti_surge_strategy_factory(
        runner=runner,
        recirculation_loop_ids=recirculation_loop_ids,
        compressors=compressors,
    )
    pressure_control_strategy = individual_asv_pressure_control_strategy_factory(
        runner=runner,
        recirculation_loop_ids=recirculation_loop_ids,
        compressors=compressors,
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

    speed_configuration: SpeedConfiguration = [
        config.value for config in solution.configuration if isinstance(config.value, SpeedConfiguration)
    ][0]

    assert new_outlet_stream.volumetric_rate_m3_per_hour == pytest.approx(
        old_outlet_stream.volumetric_rate_m3_per_hour, rel=0.001
    )  # 0.1 %
    assert new_outlet_stream.pressure_bara == pytest.approx(old_outlet_stream.pressure_bara, rel=0.001)  # 0.000001 %
    assert new_outlet_stream.density == pytest.approx(old_outlet_stream.density, rel=0.001)  # 0.1 %
    assert speed_configuration.speed == pytest.approx(shaft_old.get_speed(), rel=0.001)  # 2.1 %

    new_recirculation_rates = [
        config.value.recirculation_rate
        for config in solution.configuration
        if isinstance(config.value, RecirculationConfiguration)
    ]
    old_recirculation_rates = [
        stage_result.inlet_stream_including_asv.standard_rate_sm3_per_day
        - stage_result.inlet_stream.standard_rate_sm3_per_day
        for stage_result in old_result.stage_results
    ]

    assert new_recirculation_rates == pytest.approx(old_recirculation_rates, rel=0.01)


def test_individual_asv_anti_surge_returns_failure_when_rate_above_stonewall(
    stream_factory,
    compressor_factory,
    stage_units_factory,
    with_individual_asv,
    process_runner_factory,
    individual_asv_anti_surge_strategy_factory,
    individual_asv_rate_control_strategy_factory,
    outlet_pressure_solver_factory,
    chart_data_factory,
):
    shaft = VariableSpeedShaft()
    chart_data = chart_data_factory.from_curves(
        curves=[
            ChartCurve(
                speed_rpm=75.0,
                rate_actual_m3_hour=[50.0, 200.0],
                polytropic_head_joule_per_kg=[120_000.0, 80_000.0],
                efficiency_fraction=[0.75, 0.75],
            ),
            ChartCurve(
                speed_rpm=105.0,
                rate_actual_m3_hour=[70.0, 300.0],
                polytropic_head_joule_per_kg=[170_000.0, 110_000.0],
                efficiency_fraction=[0.75, 0.75],
            ),
        ],
        control_margin=0.0,
    )
    compressor1 = compressor_factory(chart_data=chart_data)
    compressor2 = compressor_factory(chart_data=chart_data)
    stage1_units = stage_units_factory(compressor=compressor1, shaft=shaft)
    stage2_units = stage_units_factory(compressor=compressor2, shaft=shaft)
    compressors = [compressor1, compressor2]
    individual_asvs, loops = with_individual_asv([*stage1_units, *stage2_units])
    loop_ids = [loop.get_id() for loop in loops]

    runner = process_runner_factory(units=individual_asvs, configuration_handlers=[shaft, *loops])
    anti_surge = individual_asv_anti_surge_strategy_factory(
        runner=runner, recirculation_loop_ids=loop_ids, compressors=compressors
    )
    pressure_control = individual_asv_rate_control_strategy_factory(
        runner=runner, recirculation_loop_ids=loop_ids, compressors=compressors
    )
    solver = outlet_pressure_solver_factory(
        shaft=shaft,
        runner=runner,
        anti_surge_strategy=anti_surge,
        pressure_control_strategy=pressure_control,
    )

    inlet_stream = stream_factory(standard_rate_m3_per_day=5_000_000, pressure_bara=30.0)
    assert inlet_stream.volumetric_rate_m3_per_hour > 300.0

    solution = solver.find_solution(
        pressure_constraint=FloatConstraint(75.0),
        inlet_stream=inlet_stream,
    )

    assert not solution.success


def test_individual_asv_anti_surge_single_stage_returns_failure_when_rate_above_stonewall(
    stream_factory,
    compressor_factory,
    stage_units_factory,
    with_individual_asv,
    process_runner_factory,
    individual_asv_anti_surge_strategy_factory,
    chart_data_factory,
):
    shaft = VariableSpeedShaft()
    chart_data = chart_data_factory.from_curves(
        curves=[
            ChartCurve(
                speed_rpm=75.0,
                rate_actual_m3_hour=[50.0, 200.0],
                polytropic_head_joule_per_kg=[120_000.0, 80_000.0],
                efficiency_fraction=[0.75, 0.75],
            ),
            ChartCurve(
                speed_rpm=105.0,
                rate_actual_m3_hour=[70.0, 300.0],
                polytropic_head_joule_per_kg=[170_000.0, 110_000.0],
                efficiency_fraction=[0.75, 0.75],
            ),
        ],
        control_margin=0.0,
    )
    compressor = compressor_factory(chart_data=chart_data)
    stage_units = stage_units_factory(compressor=compressor, shaft=shaft)
    compressors = [compressor]
    individual_asvs, loops = with_individual_asv(stage_units)
    loop_ids = [loop.get_id() for loop in loops]
    runner = process_runner_factory(units=individual_asvs, configuration_handlers=[shaft, *loops])
    anti_surge = individual_asv_anti_surge_strategy_factory(
        runner=runner, recirculation_loop_ids=loop_ids, compressors=compressors
    )

    inlet_stream = stream_factory(standard_rate_m3_per_day=5_000_000, pressure_bara=30.0)
    assert inlet_stream.volumetric_rate_m3_per_hour > 300.0

    runner.apply_configuration(Configuration(simulation_unit_id=shaft.get_id(), value=SpeedConfiguration(speed=105.0)))
    solution = anti_surge.apply(inlet_stream=inlet_stream)

    assert not solution.success
