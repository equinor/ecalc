import pytest

from libecalc.common.fixed_speed_pressure_control import FixedSpeedPressureControl
from libecalc.domain.process.compressor.core.train.train_evaluation_input import CompressorTrainEvaluationInput
from libecalc.domain.process.entities.shaft import VariableSpeedShaft
from libecalc.domain.process.process_solver.asv_solvers import IndividualASVRateSolver
from libecalc.domain.process.process_solver.float_constraint import FloatConstraint
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


def test_individual_asv_rate_solver_vs_legacy_train(
    variable_speed_compressor_train,
    compressor_stage_factory,
    compressor_stages,
    fluid_service,
    variable_speed_compressor_chart_data,
    chart_data_factory,
    stream_factory,
    compressor_train_stage_process_unit_factory,
):
    temperature = 300.0
    target_pressure = 90.0

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
    stages_new = [stage1_new, stage2_new]

    train_solver = IndividualASVRateSolver(
        compressors=stages_new,
        fluid_service=fluid_service,
        shaft=shaft_new,
    )
    speed_solution, recirculation_solutions = train_solver.find_individual_asv_rate_solution(
        pressure_constraint=FloatConstraint(target_pressure),
        inlet_stream=inlet_stream,
    )
    recirculation_loops = train_solver.get_recirculation_loops()
    shaft_new.set_speed(speed_solution.configuration.speed)
    current_stream = inlet_stream
    for recirculation_loop, recirculation_solution in zip(recirculation_loops, recirculation_solutions):
        recirculation_loop.set_recirculation_rate(recirculation_solution.configuration.recirculation_rate)
        current_stream = recirculation_loop.propagate_stream(inlet_stream=current_stream)
    new_outlet_stream = current_stream

    assert new_outlet_stream.volumetric_rate_m3_per_hour == pytest.approx(
        old_outlet_stream.volumetric_rate_m3_per_hour, rel=0.001
    )  # 0.1 %
    assert new_outlet_stream.pressure_bara == pytest.approx(old_outlet_stream.pressure_bara, rel=0.001)  # 0.000001 %
    assert new_outlet_stream.density == pytest.approx(old_outlet_stream.density, rel=0.001)  # 0.1 %
    assert shaft_new.get_speed() == pytest.approx(shaft_old.get_speed(), rel=0.021)  # 2.1 %

    # For now new and old recirculation rate is not expected to match - as the old train recirculates individual stages and finds a solution
    # without common asv
    new_recirculation_rates = [
        recirculation_solution.configuration.recirculation_rate for recirculation_solution in recirculation_solutions
    ]
    old_recirculation_rates = [
        stage_result.inlet_stream_including_asv.standard_rate_sm3_per_day
        - stage_result.inlet_stream.standard_rate_sm3_per_day
        for stage_result in old_result.stage_results
    ]

    assert new_recirculation_rates == pytest.approx(old_recirculation_rates, rel=0.01)
