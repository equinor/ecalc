import uuid

import pytest

from libecalc.common.fixed_speed_pressure_control import FixedSpeedPressureControl, InterstagePressureControl
from libecalc.domain.process.compressor.core.train.compressor_train_common_shaft import CompressorTrainCommonShaft
from libecalc.domain.process.compressor.core.train.train_evaluation_input import CompressorTrainEvaluationInput
from libecalc.domain.process.entities.process_units.mixer import Mixer
from libecalc.domain.process.entities.process_units.splitter import Splitter
from libecalc.domain.process.entities.shaft import VariableSpeedShaft
from libecalc.domain.process.process_solver.boundary import Boundary
from libecalc.domain.process.process_solver.float_constraint import FloatConstraint
from libecalc.domain.process.process_solver.outlet_pressure_solver import OutletPressureSolver

from .conftest import make_variable_speed_chart_data


@pytest.mark.parametrize("pd_target", [92.0, 150.0])
def test_two_stage_train_with_interstage_pressure_vs_legacy(
    pd_target,
    stream_factory,
    chart_data_factory,
    fluid_service,
    stage_units_factory,
    with_individual_asv,
    process_runner_factory,
    individual_asv_anti_surge_strategy_factory,
    individual_asv_rate_control_strategy_factory,
    multi_pressure_solver_factory,
    compressor_stage_factory,
    root_finding_strategy,
):
    temperature = 300.0
    interstage_pressure_target = 60.0  # bara
    target_pressure = pd_target

    inlet_stream = stream_factory(
        standard_rate_m3_per_day=500_000.0,
        pressure_bara=30.0,
        temperature_kelvin=temperature,
    )
    export_rate_sm3_per_day = 50_000.0

    q0 = float(inlet_stream.volumetric_rate_m3_per_hour)

    low_pressure_chart_data = make_variable_speed_chart_data(
        chart_data_factory,
        min_rate=0.0,
        max_rate=q0 * 10.0,
        head_hi=150_000.0,
        head_lo=50_000.0,
        eff=0.75,
    )
    high_pressure_chart_data = make_variable_speed_chart_data(
        chart_data_factory,
        min_rate=0.0,
        max_rate=q0 * 10.0,
        head_hi=120_000.0,
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
        interstage_pressure_control=InterstagePressureControl(
            upstream_pressure_control=FixedSpeedPressureControl.INDIVIDUAL_ASV_RATE,
            downstream_pressure_control=FixedSpeedPressureControl.INDIVIDUAL_ASV_RATE,
        ),
    )
    train_old = CompressorTrainCommonShaft(
        stages=[low_pressure_stage_old, high_pressure_stage_old],
        shaft=shaft_old,
        fluid_service=fluid_service,
        energy_usage_adjustment_constant=0,
        energy_usage_adjustment_factor=1,
        stage_number_interstage_pressure=1,
    )
    train_old._fluid_model = [inlet_stream.fluid_model, None]
    old_result = train_old.evaluate_given_constraints(
        CompressorTrainEvaluationInput(
            suction_pressure=inlet_stream.pressure_bara,
            discharge_pressure=target_pressure,
            interstage_pressure=interstage_pressure_target,
            rates=[inlet_stream.standard_rate_sm3_per_day, export_rate_sm3_per_day],
        )
    )

    shaft_new = VariableSpeedShaft()
    low_pressure_units_raw = stage_units_factory(
        chart_data=low_pressure_chart_data, shaft=shaft_new, temperature_kelvin=temperature
    )
    low_pressure_units_wrapped, low_pressure_loop_ids, low_pressure_compressors = with_individual_asv(
        low_pressure_units_raw
    )
    low_pressure_runner = process_runner_factory(units=low_pressure_units_wrapped, shaft=shaft_new)

    high_pressure_units_raw = stage_units_factory(
        chart_data=high_pressure_chart_data, shaft=shaft_new, temperature_kelvin=temperature
    )
    splitter = Splitter(process_unit_id=uuid.uuid4(), fluid_service=fluid_service, rate=export_rate_sm3_per_day)
    high_pressure_units_wrapped, high_pressure_loop_ids, high_pressure_compressors = with_individual_asv(
        high_pressure_units_raw
    )
    high_pressure_runner = process_runner_factory(units=[splitter, *high_pressure_units_wrapped], shaft=shaft_new)

    speed_boundary = Boundary(
        min=max(
            max(c.get_speed_boundary().min for c in low_pressure_compressors),
            max(c.get_speed_boundary().min for c in high_pressure_compressors),
        ),
        max=min(
            min(c.get_speed_boundary().max for c in low_pressure_compressors),
            min(c.get_speed_boundary().max for c in high_pressure_compressors),
        ),
    )
    low_pressure_segment = OutletPressureSolver(
        shaft_id=shaft_new.get_id(),
        runner=low_pressure_runner,
        anti_surge_strategy=individual_asv_anti_surge_strategy_factory(
            runner=low_pressure_runner,
            recirculation_loop_ids=low_pressure_loop_ids,
            compressors=low_pressure_compressors,
        ),
        pressure_control_strategy=individual_asv_rate_control_strategy_factory(
            runner=low_pressure_runner,
            recirculation_loop_ids=low_pressure_loop_ids,
            compressors=low_pressure_compressors,
        ),
        root_finding_strategy=root_finding_strategy,
        speed_boundary=speed_boundary,
    )
    high_pressure_segment = OutletPressureSolver(
        shaft_id=shaft_new.get_id(),
        runner=high_pressure_runner,
        anti_surge_strategy=individual_asv_anti_surge_strategy_factory(
            runner=high_pressure_runner,
            recirculation_loop_ids=high_pressure_loop_ids,
            compressors=high_pressure_compressors,
        ),
        pressure_control_strategy=individual_asv_rate_control_strategy_factory(
            runner=high_pressure_runner,
            recirculation_loop_ids=high_pressure_loop_ids,
            compressors=high_pressure_compressors,
        ),
        root_finding_strategy=root_finding_strategy,
        speed_boundary=speed_boundary,
    )

    solver = multi_pressure_solver_factory(
        segments=[low_pressure_segment, high_pressure_segment],
    )
    solution = solver.find_solution(
        pressure_targets=[
            FloatConstraint(interstage_pressure_target),
            FloatConstraint(target_pressure),
        ],
        inlet_stream=inlet_stream,
    )
    interstage_stream = low_pressure_runner.run(inlet_stream=inlet_stream)
    new_outlet_stream = high_pressure_runner.run(inlet_stream=interstage_stream)

    assert solution.success
    assert interstage_stream.pressure_bara == pytest.approx(interstage_pressure_target, rel=0.001)
    assert new_outlet_stream.pressure_bara == pytest.approx(target_pressure, rel=0.001)
    assert interstage_stream.pressure_bara == pytest.approx(
        old_result.stage_results[0].outlet_stream.pressure_bara, rel=0.001
    )
    assert new_outlet_stream.pressure_bara == pytest.approx(old_result.outlet_stream.pressure_bara, rel=0.001)


@pytest.mark.parametrize("pd_target", [130.0, 180.0])
def test_three_stage_train_with_mixers_and_splitters_at_interstage(
    pd_target,
    stream_factory,
    chart_data_factory,
    fluid_service,
    stage_units_factory,
    with_individual_asv,
    process_runner_factory,
    individual_asv_anti_surge_strategy_factory,
    individual_asv_rate_control_strategy_factory,
    multi_pressure_solver_factory,
    root_finding_strategy,
):
    """LP → [Mixer1, Mixer2] → MP → [Splitter1, Splitter2] → HP, with interstage pressures at both junctions."""
    temperature = 300.0
    interstage_1 = 60.0  # bara: after LP, before mixers+MP
    interstage_2 = 100.0  # bara: after MP+splitters, before HP
    target_pressure = pd_target

    inlet_stream = stream_factory(
        standard_rate_m3_per_day=500_000.0,
        pressure_bara=30.0,
        temperature_kelvin=temperature,
    )
    injection_rate_sm3_per_day = 50_000.0
    export_rate_sm3_per_day = 30_000.0

    q0 = float(inlet_stream.volumetric_rate_m3_per_hour)

    low_pressure_chart_data = make_variable_speed_chart_data(
        chart_data_factory,
        min_rate=0.0,
        max_rate=q0 * 10.0,
        head_hi=150_000.0,
        head_lo=50_000.0,
        eff=0.75,
    )
    medium_pressure_chart_data = make_variable_speed_chart_data(
        chart_data_factory,
        min_rate=0.0,
        max_rate=q0 * 15.0,
        head_hi=80_000.0,
        head_lo=20_000.0,
        eff=0.75,
    )
    high_pressure_chart_data = make_variable_speed_chart_data(
        chart_data_factory,
        min_rate=0.0,
        max_rate=q0 * 15.0,
        head_hi=100_000.0,
        head_lo=15_000.0,
        eff=0.72,
    )

    shaft = VariableSpeedShaft()

    low_pressure_units_raw = stage_units_factory(
        chart_data=low_pressure_chart_data, shaft=shaft, temperature_kelvin=temperature
    )
    low_pressure_units_wrapped, low_pressure_loop_ids, low_pressure_compressors = with_individual_asv(
        low_pressure_units_raw
    )
    low_pressure_runner = process_runner_factory(units=low_pressure_units_wrapped, shaft=shaft)

    mixer1 = Mixer(process_unit_id=uuid.uuid4(), fluid_service=fluid_service)
    mixer2 = Mixer(process_unit_id=uuid.uuid4(), fluid_service=fluid_service)
    medium_pressure_units_raw = stage_units_factory(
        chart_data=medium_pressure_chart_data, shaft=shaft, temperature_kelvin=temperature
    )
    medium_pressure_units_wrapped, medium_pressure_loop_ids, medium_pressure_compressors = with_individual_asv(
        medium_pressure_units_raw
    )
    medium_pressure_runner = process_runner_factory(units=[mixer1, mixer2, *medium_pressure_units_wrapped], shaft=shaft)

    splitter1 = Splitter(process_unit_id=uuid.uuid4(), fluid_service=fluid_service, rate=export_rate_sm3_per_day)
    splitter2 = Splitter(process_unit_id=uuid.uuid4(), fluid_service=fluid_service, rate=export_rate_sm3_per_day)
    high_pressure_units_raw = stage_units_factory(
        chart_data=high_pressure_chart_data, shaft=shaft, temperature_kelvin=temperature
    )
    high_pressure_units_wrapped, high_pressure_loop_ids, high_pressure_compressors = with_individual_asv(
        high_pressure_units_raw
    )
    high_pressure_runner = process_runner_factory(
        units=[splitter1, splitter2, *high_pressure_units_wrapped], shaft=shaft
    )

    injection_stream = stream_factory(
        standard_rate_m3_per_day=injection_rate_sm3_per_day,
        pressure_bara=interstage_1,
        temperature_kelvin=temperature,
    )
    mixer1.set_stream(injection_stream)
    mixer2.set_stream(injection_stream)

    speed_boundary = Boundary(
        min=max(
            max(c.get_speed_boundary().min for c in low_pressure_compressors),
            max(c.get_speed_boundary().min for c in medium_pressure_compressors),
            max(c.get_speed_boundary().min for c in high_pressure_compressors),
        ),
        max=min(
            min(c.get_speed_boundary().max for c in low_pressure_compressors),
            min(c.get_speed_boundary().max for c in medium_pressure_compressors),
            min(c.get_speed_boundary().max for c in high_pressure_compressors),
        ),
    )

    def make_segment(runner, loop_ids, compressors):
        return OutletPressureSolver(
            shaft_id=shaft.get_id(),
            runner=runner,
            anti_surge_strategy=individual_asv_anti_surge_strategy_factory(
                runner=runner,
                recirculation_loop_ids=loop_ids,
                compressors=compressors,
            ),
            pressure_control_strategy=individual_asv_rate_control_strategy_factory(
                runner=runner,
                recirculation_loop_ids=loop_ids,
                compressors=compressors,
            ),
            root_finding_strategy=root_finding_strategy,
            speed_boundary=speed_boundary,
        )

    solver = multi_pressure_solver_factory(
        segments=[
            make_segment(low_pressure_runner, low_pressure_loop_ids, low_pressure_compressors),
            make_segment(medium_pressure_runner, medium_pressure_loop_ids, medium_pressure_compressors),
            make_segment(high_pressure_runner, high_pressure_loop_ids, high_pressure_compressors),
        ],
    )
    solution = solver.find_solution(
        pressure_targets=[
            FloatConstraint(interstage_1),
            FloatConstraint(interstage_2),
            FloatConstraint(target_pressure),
        ],
        inlet_stream=inlet_stream,
    )

    low_pressure_outlet = low_pressure_runner.run(inlet_stream=inlet_stream)
    medium_pressure_outlet = medium_pressure_runner.run(inlet_stream=low_pressure_outlet)
    high_pressure_outlet = high_pressure_runner.run(inlet_stream=medium_pressure_outlet)

    assert solution.success
    assert low_pressure_outlet.pressure_bara == pytest.approx(interstage_1, rel=0.001)
    assert medium_pressure_outlet.pressure_bara == pytest.approx(interstage_2, rel=0.001)
    assert high_pressure_outlet.pressure_bara == pytest.approx(target_pressure, rel=0.001)
