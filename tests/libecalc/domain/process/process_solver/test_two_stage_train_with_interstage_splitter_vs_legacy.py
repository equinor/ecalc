import pytest

from libecalc.common.fixed_speed_pressure_control import FixedSpeedPressureControl
from libecalc.domain.process.compressor.core.train.train_evaluation_input import CompressorTrainEvaluationInput
from libecalc.domain.process.entities.process_units.splitter import Splitter
from libecalc.domain.process.entities.shaft import VariableSpeedShaft
from libecalc.domain.process.process_solver.float_constraint import FloatConstraint
from libecalc.domain.process.process_solver.solvers.recirculation_solver import RecirculationConfiguration


@pytest.mark.parametrize("pd_target", [50.0, 92.0, 150.0])
def test_two_stage_train_with_interstage_splitter_vs_legacy(
    pd_target,
    variable_speed_compressor_train,
    compressor_stage_factory,
    stream_factory,
    chart_data_factory,
    fluid_service,
    compressor_factory,
    stage_units_factory,
    with_individual_asv,
    process_runner_factory,
    individual_asv_anti_surge_strategy_factory,
    individual_asv_rate_control_strategy_factory,
    outlet_pressure_solver_factory,
    variable_speed_chart_data_factory,
):
    temperature = 300.0
    target_pressure = pd_target

    inlet_stream = stream_factory(
        standard_rate_m3_per_day=500_000.0,
        pressure_bara=30.0,
        temperature_kelvin=temperature,
    )
    export_rate_sm3_per_day = 50_000.0

    q0 = float(inlet_stream.volumetric_rate_m3_per_hour)

    low_pressure_chart_data = variable_speed_chart_data_factory(
        chart_data_factory,
        min_rate=q0 * 1.5,
        max_rate=q0 * 10.0,
        head_hi=80_000.0,
        head_lo=40_000.0,
        eff=0.75,
    )
    high_pressure_chart_data = variable_speed_chart_data_factory(
        chart_data_factory,
        min_rate=0.0,
        max_rate=q0 * 20.0,
        head_hi=60_000.0,
        head_lo=30_000.0,
        eff=0.72,
    )

    shaft_old = VariableSpeedShaft()
    low_pressure_stage_old = compressor_stage_factory(
        compressor_chart_data=low_pressure_chart_data,
        shaft=shaft_old,
        inlet_temperature_kelvin=temperature,
    )
    high_pressure_stage_old = compressor_stage_factory(
        compressor_chart_data=high_pressure_chart_data,
        shaft=shaft_old,
        inlet_temperature_kelvin=temperature,
        number_of_output_ports_stage=1,
    )
    train_old = variable_speed_compressor_train(
        stages=[low_pressure_stage_old, high_pressure_stage_old],
        shaft=shaft_old,
        pressure_control=FixedSpeedPressureControl.INDIVIDUAL_ASV_RATE,
    )
    train_old._fluid_model = [inlet_stream.fluid_model, None]
    old_result = train_old.evaluate_given_constraints(
        CompressorTrainEvaluationInput(
            suction_pressure=inlet_stream.pressure_bara,
            discharge_pressure=target_pressure,
            rates=[inlet_stream.standard_rate_sm3_per_day, export_rate_sm3_per_day],
        )
    )
    old_outlet_stream = old_result.outlet_stream

    shaft_new = VariableSpeedShaft()
    lp_compressor = compressor_factory(chart_data=low_pressure_chart_data)
    hp_compressor = compressor_factory(chart_data=high_pressure_chart_data)
    low_pressure_stage_new = stage_units_factory(
        compressor=lp_compressor,
        shaft=shaft_new,
        temperature_kelvin=temperature,
    )
    high_pressure_stage_new = stage_units_factory(
        compressor=hp_compressor,
        shaft=shaft_new,
        temperature_kelvin=temperature,
    )
    interstage_splitter = Splitter(
        fluid_service=fluid_service,
        rate=export_rate_sm3_per_day,
    )
    all_units = [*low_pressure_stage_new, interstage_splitter, *high_pressure_stage_new]
    compressors = [lp_compressor, hp_compressor]
    units_new, loops = with_individual_asv(all_units)
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
    config_dict = {config.configuration_handler_id: config for config in solution.configuration}
    speed_configuration = config_dict[shaft_new.get_id()].value
    runner.apply_configurations(solution.configuration)
    new_outlet_stream = runner.run(inlet_stream=inlet_stream)

    assert new_outlet_stream.pressure_bara == pytest.approx(old_outlet_stream.pressure_bara, rel=0.001)
    assert new_outlet_stream.volumetric_rate_m3_per_hour == pytest.approx(
        old_outlet_stream.volumetric_rate_m3_per_hour, rel=0.001
    )
    assert new_outlet_stream.density == pytest.approx(old_outlet_stream.density, rel=0.001)
    assert speed_configuration.speed == pytest.approx(shaft_old.get_speed(), rel=0.001)

    new_low_pressure_recirculation = [
        config.value.recirculation_rate
        for config in solution.configuration
        if isinstance(config.value, RecirculationConfiguration)
    ][0]
    old_low_pressure_recirculation = (
        old_result.stage_results[0].inlet_stream_including_asv.standard_rate_sm3_per_day
        - old_result.stage_results[0].inlet_stream.standard_rate_sm3_per_day
    )
    assert old_low_pressure_recirculation == pytest.approx(new_low_pressure_recirculation, rel=0.01)
