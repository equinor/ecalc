import numpy as np
import pytest

from libecalc.common.utils.ecalc_uuid import ecalc_id_generator
from libecalc.domain.component_validation_error import ComponentValidationException
from libecalc.domain.process.compressor.core.train.simplified_train.simplified_train import CompressorTrainSimplified
from libecalc.domain.process.entities.process_units.choke import Choke
from libecalc.domain.process.entities.process_units.compressor import Compressor
from libecalc.domain.process.process_pipeline.process_pipeline import ProcessPipeline, ProcessPipelineId
from libecalc.domain.process.process_pipeline.process_unit import ProcessUnitId
from libecalc.domain.process.process_solver.equal_ratio_outlet_pressure_calculator import (
    EqualRatioOutletPressureCalculator,
)
from libecalc.domain.process.process_solver.float_constraint import FloatConstraint
from libecalc.domain.process.process_solver.solver import SolverFailureStatus


def test_single_stage_simplified_solver_meets_target(stream_factory, fluid_service, make_compressor):
    """Single-stage simplified solver should produce outlet at target pressure."""
    system = ProcessPipeline(
        process_pipeline_id=ProcessPipelineId(ecalc_id_generator()), stream_propagators=[make_compressor()]
    )
    solver = EqualRatioOutletPressureCalculator(system=system, fluid_service=fluid_service)

    inlet = stream_factory(standard_rate_m3_per_day=400_000, pressure_bara=20.0)
    target = FloatConstraint(50.0, abs_tol=1.0)

    solution = solver.find_solution(pressure_constraint=target, inlet_stream=inlet)

    assert solution.success


def test_two_stage_simplified_solver_meets_target(stream_factory, fluid_service, make_compressor):
    """Two-stage simplified solver should split ratio equally and produce correct outlet."""
    system = ProcessPipeline(
        process_pipeline_id=ProcessPipelineId(ecalc_id_generator()),
        stream_propagators=[make_compressor(), make_compressor()],
    )
    solver = EqualRatioOutletPressureCalculator(system=system, fluid_service=fluid_service)

    inlet = stream_factory(standard_rate_m3_per_day=400_000, pressure_bara=20.0)
    target = FloatConstraint(80.0, abs_tol=2.0)

    solution = solver.find_solution(pressure_constraint=target, inlet_stream=inlet)

    assert solution.success
    assert len(solution.configuration) == 2


def test_stonewall_on_excess_inlet_rate_reports_failure(stream_factory, fluid_service, make_compressor):
    """When inlet actual rate exceeds the chart's max-flow at the required head, find_solution
    must return a failure with MAXIMUM_ACHIEVABLE_DISCHARGE_PRESSURE_BELOW_TARGET — not silently
    succeed with bogus zero recirculation."""
    small_compressor = make_compressor(min_rate=300.0, max_rate=1000.0)
    pipeline_id = ProcessPipelineId(ecalc_id_generator())
    system = ProcessPipeline(process_pipeline_id=pipeline_id, stream_propagators=[small_compressor])
    solver = EqualRatioOutletPressureCalculator(system=system, fluid_service=fluid_service)

    inlet = stream_factory(standard_rate_m3_per_day=400_000, pressure_bara=20.0)
    target = FloatConstraint(50.0, abs_tol=1.0)

    solution = solver.find_solution(pressure_constraint=target, inlet_stream=inlet)

    assert not solution.success
    assert solution.failure_event is not None
    assert solution.failure_event.status == SolverFailureStatus.MAXIMUM_ACHIEVABLE_DISCHARGE_PRESSURE_BELOW_TARGET
    assert solution.failure_event.source_id == pipeline_id


def test_temperature_setter_before_compressor_is_applied(
    stream_factory, fluid_service, make_compressor, make_temperature_setter
):
    """TemperatureSetter before a compressor should set inlet temperature before compression.

    Configuration list should contain exactly one entry (only the Compressor produces config).
    """
    system_with_setter = ProcessPipeline(
        process_pipeline_id=ProcessPipelineId(ecalc_id_generator()),
        stream_propagators=[make_temperature_setter(temperature_kelvin=303.15), make_compressor()],
    )
    system_without_setter = ProcessPipeline(
        process_pipeline_id=ProcessPipelineId(ecalc_id_generator()), stream_propagators=[make_compressor()]
    )

    hot_inlet = stream_factory(standard_rate_m3_per_day=400_000, pressure_bara=20.0, temperature_kelvin=373.15)
    target = FloatConstraint(50.0, abs_tol=1.0)

    sol_with = EqualRatioOutletPressureCalculator(system=system_with_setter, fluid_service=fluid_service).find_solution(
        pressure_constraint=target, inlet_stream=hot_inlet
    )
    sol_without = EqualRatioOutletPressureCalculator(
        system=system_without_setter, fluid_service=fluid_service
    ).find_solution(pressure_constraint=target, inlet_stream=hot_inlet)

    assert sol_with.success
    assert sol_without.success
    assert len(sol_with.configuration) == 1


def test_two_stage_with_liquid_remover_and_temperature_setter(
    stream_factory,
    fluid_service,
    make_compressor,
    make_temperature_setter,
    make_liquid_remover,
):
    """A realistic two-stage train: TemperatureSetter + Compressor + LiquidRemover + TemperatureSetter + Compressor."""
    system = ProcessPipeline(
        process_pipeline_id=ProcessPipelineId(ecalc_id_generator()),
        stream_propagators=[
            make_temperature_setter(temperature_kelvin=303.15),
            make_compressor(),
            make_liquid_remover(),
            make_temperature_setter(temperature_kelvin=303.15),
            make_compressor(),
        ],
    )
    solver = EqualRatioOutletPressureCalculator(system=system, fluid_service=fluid_service)

    inlet = stream_factory(standard_rate_m3_per_day=400_000, pressure_bara=20.0)
    target = FloatConstraint(80.0, abs_tol=2.0)

    solution = solver.find_solution(pressure_constraint=target, inlet_stream=inlet)

    assert solution.success
    assert len(solution.configuration) == 2


def test_choke_in_pipeline_raises_at_construction(make_compressor, fluid_service):
    """A Choke in the pipeline invalidates the equal-ratio assumption and must be rejected."""
    choke = Choke(
        process_unit_id=ProcessUnitId(ecalc_id_generator()),
        fluid_service=fluid_service,
        pressure_change=5.0,
    )
    system = ProcessPipeline(
        process_pipeline_id=ProcessPipelineId(ecalc_id_generator()),
        stream_propagators=[make_compressor(), choke, make_compressor()],
    )
    with pytest.raises(ComponentValidationException, match="Choke"):
        EqualRatioOutletPressureCalculator(system=system, fluid_service=fluid_service)


def test_get_max_standard_rate_matches_legacy_simplified_train(
    fluid_service,
    fluid_model_rich,
    chart_data_factory,
    compressor_stages,
    make_temperature_setter,
    make_liquid_remover,
):
    """Mirror legacy `test_compressor_train_simplified_known_stages_generic_chart`:
    EqualRatioOutletPressureCalculator.get_max_standard_rate must match
    CompressorTrainSimplified.get_max_standard_rate for the same 2-stage generic-chart setup.
    """
    suction_pressures = np.asarray([36.0, 31.0, 21.0, 19.0, 18.0, 18.0, 18.0, 18.0])
    discharge_pressures = np.asarray([250.0, 250.0, 200.0, 200.0, 200.0, 200.0, 200.0, 200.0])

    chart_a = chart_data_factory.from_design_point(efficiency=0.75, rate=15848.089397866604, head=135478.5333104937)
    chart_b = chart_data_factory.from_design_point(efficiency=0.75, rate=4539.170738284835, head=116082.08687178302)

    legacy_stages = [
        compressor_stages(chart_data=chart_a, remove_liquid_after_cooling=True)[0],
        compressor_stages(chart_data=chart_b, remove_liquid_after_cooling=True)[0],
    ]
    legacy = CompressorTrainSimplified(
        stages=legacy_stages,
        fluid_service=fluid_service,
        energy_usage_adjustment_constant=0,
        energy_usage_adjustment_factor=1,
    )
    expected = legacy.get_max_standard_rate(
        suction_pressures=suction_pressures,
        discharge_pressures=discharge_pressures,
        fluid_model=fluid_model_rich,
    )

    def _make_compressor(chart):
        return Compressor(
            process_unit_id=ProcessUnitId(ecalc_id_generator()),
            compressor_chart=chart,
            fluid_service=fluid_service,
        )

    pipeline = ProcessPipeline(
        process_pipeline_id=ProcessPipelineId(ecalc_id_generator()),
        stream_propagators=[
            make_temperature_setter(temperature_kelvin=303.15),
            _make_compressor(chart_a),
            make_liquid_remover(),
            make_temperature_setter(temperature_kelvin=303.15),
            _make_compressor(chart_b),
        ],
    )
    calculator = EqualRatioOutletPressureCalculator(system=pipeline, fluid_service=fluid_service)

    actual = []
    for suction, discharge in zip(suction_pressures, discharge_pressures):
        inlet = fluid_service.create_stream_from_standard_rate(
            fluid_model=fluid_model_rich,
            pressure_bara=float(suction),
            temperature_kelvin=303.15,
            standard_rate_m3_per_day=1.0,
        )
        actual.append(
            calculator.get_max_standard_rate(
                pressure_constraint=FloatConstraint(float(discharge), abs_tol=1.0),
                inlet_stream=inlet,
            )
        )

    np.testing.assert_allclose(actual, expected, rtol=1e-3)


def test_find_solution_matches_legacy_simplified_train_recirculation(
    fluid_service,
    fluid_model_rich,
    chart_data_factory,
    compressor_stages,
    make_temperature_setter,
    make_liquid_remover,
):
    """Solve the same 2-stage train with both implementations and verify per-stage
    recirculation (ASV add-back) matches at every operating point.

    Legacy stage_results expose mass_rate_kg_per_hr (gross) and mass_rate_before_asv_kg_per_hr
    (net); their difference is the recirc mass added by ASV. The new calculator's
    RecirculationConfiguration.recirculation_rate is the same quantity in std m3/day.
    """
    rates = np.asarray(
        [15478059.4, 14296851.66, 9001365.137, 7921594.316, 5857638.265, 4012786.153, 2920238.089, 2398857.123]
    )
    suction_pressures = np.asarray([36.0, 31.0, 21.0, 19.0, 18.0, 18.0, 18.0, 18.0])
    discharge_pressures = np.asarray([250.0, 250.0, 200.0, 200.0, 200.0, 200.0, 200.0, 200.0])

    chart_a = chart_data_factory.from_design_point(efficiency=0.75, rate=15848.089397866604, head=135478.5333104937)
    chart_b = chart_data_factory.from_design_point(efficiency=0.75, rate=4539.170738284835, head=116082.08687178302)

    legacy_stages = [
        compressor_stages(chart_data=chart_a, remove_liquid_after_cooling=True)[0],
        compressor_stages(chart_data=chart_b, remove_liquid_after_cooling=True)[0],
    ]
    legacy = CompressorTrainSimplified(
        stages=legacy_stages,
        fluid_service=fluid_service,
        energy_usage_adjustment_constant=0,
        energy_usage_adjustment_factor=1,
    )
    legacy.set_evaluation_input(
        fluid_model=fluid_model_rich,
        rate=rates,
        suction_pressure=suction_pressures,
        discharge_pressure=discharge_pressures,
    )
    legacy_results = legacy.evaluate()

    def _make_compressor(chart):
        return Compressor(
            process_unit_id=ProcessUnitId(ecalc_id_generator()),
            compressor_chart=chart,
            fluid_service=fluid_service,
        )

    pipeline = ProcessPipeline(
        process_pipeline_id=ProcessPipelineId(ecalc_id_generator()),
        stream_propagators=[
            make_temperature_setter(temperature_kelvin=303.15),
            _make_compressor(chart_a),
            make_liquid_remover(),
            make_temperature_setter(temperature_kelvin=303.15),
            _make_compressor(chart_b),
        ],
    )
    calculator = EqualRatioOutletPressureCalculator(system=pipeline, fluid_service=fluid_service)

    expected_recirc_stage0_sm3 = []
    actual_recirc_stage0_sm3 = []
    for i, (rate, suction, discharge) in enumerate(zip(rates, suction_pressures, discharge_pressures)):
        inlet = fluid_service.create_stream_from_standard_rate(
            fluid_model=fluid_model_rich,
            pressure_bara=float(suction),
            temperature_kelvin=303.15,
            standard_rate_m3_per_day=float(rate),
        )
        solution = calculator.find_solution(
            pressure_constraint=FloatConstraint(float(discharge), abs_tol=1.0),
            inlet_stream=inlet,
        )
        assert solution.success, f"point {i}: new calculator failed"
        assert len(solution.configuration) == 2
        actual_recirc_stage0_sm3.append(solution.configuration[0].value.recirculation_rate)

        legacy_recirc_kg = (
            legacy_results.stage_results[0].mass_rate_kg_per_hr[i]
            - legacy_results.stage_results[0].mass_rate_before_asv_kg_per_hr[i]
        )
        expected_recirc_stage0_sm3.append(
            fluid_service.mass_rate_to_standard_rate(fluid_model=fluid_model_rich, mass_rate_kg_per_h=legacy_recirc_kg)
        )

    np.testing.assert_allclose(actual_recirc_stage0_sm3, expected_recirc_stage0_sm3, rtol=1e-2, atol=1.0)
