"""Tests for MultiShaftEqualRatioSolver."""

import pytest

from libecalc.common.utils.ecalc_uuid import ecalc_id_generator
from libecalc.domain.process.value_objects.chart import ChartCurve
from libecalc.process.process_pipeline.process_pipeline import ProcessPipelineId
from libecalc.process.process_pipeline.process_unit import ProcessUnitId
from libecalc.process.process_solver.anti_surge.individual_asv import IndividualASVAntiSurgeStrategy
from libecalc.process.process_solver.configuration import ConfigurationHandlerId, SpeedConfiguration
from libecalc.process.process_solver.float_constraint import FloatConstraint
from libecalc.process.process_solver.multi_shaft_equal_ratio_solver import MultiShaftEqualRatioSolver
from libecalc.process.process_solver.outlet_pressure_solver import OutletPressureSolver
from libecalc.process.process_solver.pressure_control.individual_asv import IndividualASVPressureControlStrategy
from libecalc.process.process_solver.process_pipeline_runner import ProcessPipelineRunner
from libecalc.process.process_solver.recirculation_loop import RecirculationLoop
from libecalc.process.process_units.compressor import Compressor
from libecalc.process.process_units.direct_mixer import DirectMixer
from libecalc.process.process_units.direct_splitter import DirectSplitter
from libecalc.process.process_units.temperature_setter import TemperatureSetter
from libecalc.process.shaft import VariableSpeedShaft
from libecalc.testing.chart_data_factory import ChartDataFactory


def make_variable_speed_chart(min_rate: float, max_rate: float, head_hi: float, head_lo: float, eff: float = 0.75):
    """Five affinity-law-scaled speed curves (60–100 rpm)."""
    curves = []
    for n in [60.0, 70.0, 80.0, 90.0, 100.0]:
        f = n / 100.0
        curves.append(
            ChartCurve(
                speed_rpm=n,
                rate_actual_m3_hour=[min_rate * f, max_rate * f],
                polytropic_head_joule_per_kg=[head_hi * f**2, head_lo * f**2],
                efficiency_fraction=[eff, eff],
            )
        )
    return ChartDataFactory.from_curves(curves, control_margin=0.0)


def make_process_pipeline(
    *,
    min_rate: float,
    max_rate: float,
    head_hi: float,
    head_lo: float,
    inlet_temperature_kelvin: float,
    fluid_service,
    root_finding_strategy,
) -> OutletPressureSolver:
    """One independently-shafted process pipeline: TemperatureSetter → Compressor with individual ASV."""
    chart_data = make_variable_speed_chart(min_rate, max_rate, head_hi, head_lo)

    compressor = Compressor(
        compressor_chart=chart_data,
        fluid_service=fluid_service,
        process_unit_id=ProcessUnitId(ecalc_id_generator()),
    )

    shaft = VariableSpeedShaft(configuration_handler_id=ConfigurationHandlerId(ecalc_id_generator()))
    shaft.connect(compressor)

    mixer = DirectMixer()
    splitter = DirectSplitter()
    loop = RecirculationLoop(
        mixer=mixer,
        splitter=splitter,
        configuration_handler_id=ConfigurationHandlerId(ecalc_id_generator()),
    )

    runner = ProcessPipelineRunner(
        configuration_handlers=[shaft, loop],
        units=[
            TemperatureSetter(required_temperature_kelvin=inlet_temperature_kelvin, fluid_service=fluid_service),
            mixer,
            compressor,
            splitter,
        ],
    )

    anti_surge = IndividualASVAntiSurgeStrategy(
        recirculation_loop_ids=[loop.get_id()],
        compressors=[compressor],
        simulator=runner,
    )
    pressure_control = IndividualASVPressureControlStrategy(
        simulator=runner,
        recirculation_loop_ids=[loop.get_id()],
        compressors=[compressor],
        root_finding_strategy=root_finding_strategy,
    )

    return OutletPressureSolver(
        shaft_id=shaft.get_id(),
        process_pipeline_id=ProcessPipelineId(ecalc_id_generator()),
        runner=runner,
        anti_surge_strategy=anti_surge,
        pressure_control_strategy=pressure_control,
        root_finding_strategy=root_finding_strategy,
        speed_boundary=shaft.get_speed_boundary(),
    )


@pytest.fixture
def pipeline_kwargs(fluid_service, root_finding_strategy):
    return {
        "head_hi": 200_000,
        "head_lo": 140_000,
        "inlet_temperature_kelvin": 303.15,
        "fluid_service": fluid_service,
        "root_finding_strategy": root_finding_strategy,
    }


def test_three_shaft_train_hits_target_pressure(stream_factory, pipeline_kwargs):
    pipelines = [
        make_process_pipeline(min_rate=200, max_rate=5000, **pipeline_kwargs),
        make_process_pipeline(min_rate=150, max_rate=3500, **pipeline_kwargs),
        make_process_pipeline(min_rate=100, max_rate=2500, **pipeline_kwargs),
    ]
    solver = MultiShaftEqualRatioSolver(process_pipelines=pipelines)
    inlet = stream_factory(standard_rate_m3_per_day=1_500_000.0, pressure_bara=30.0, temperature_kelvin=303.15)

    solution = solver.find_solution(FloatConstraint(270.0, abs_tol=5.0), inlet)

    assert solution.success, f"Expected success; failure: {solution.failure_event}"


def test_each_shaft_runs_at_different_speed(stream_factory, pipeline_kwargs):
    """Real-gas effects cause each pipeline to need a different shaft speed."""
    pipelines = [
        make_process_pipeline(min_rate=200, max_rate=5000, **pipeline_kwargs),
        make_process_pipeline(min_rate=150, max_rate=3500, **pipeline_kwargs),
        make_process_pipeline(min_rate=100, max_rate=2500, **pipeline_kwargs),
    ]
    solver = MultiShaftEqualRatioSolver(process_pipelines=pipelines)
    inlet = stream_factory(standard_rate_m3_per_day=1_500_000.0, pressure_bara=30.0, temperature_kelvin=303.15)

    solution = solver.find_solution(FloatConstraint(270.0, abs_tol=5.0), inlet)

    speeds = [c.value.speed for c in solution.configuration if isinstance(c.value, SpeedConfiguration)]
    assert len(speeds) == 3
    assert len(set(speeds)) == 3, f"expected three distinct speeds, got {speeds}"


def test_intercooler_changes_stage_speed(stream_factory, fluid_service, root_finding_strategy):
    """Warmer inlet temperature changes the required shaft speed."""
    common = {
        "min_rate": 200,
        "max_rate": 5000,
        "head_hi": 200_000,
        "head_lo": 140_000,
        "fluid_service": fluid_service,
        "root_finding_strategy": root_finding_strategy,
    }

    cool = [make_process_pipeline(**common, inlet_temperature_kelvin=303.15) for _ in range(3)]
    warm = [make_process_pipeline(**common, inlet_temperature_kelvin=360.0) for _ in range(3)]

    inlet = stream_factory(standard_rate_m3_per_day=1_500_000.0, pressure_bara=30.0, temperature_kelvin=303.15)
    constraint = FloatConstraint(270.0, abs_tol=5.0)

    sol_cool = MultiShaftEqualRatioSolver(process_pipelines=cool).find_solution(constraint, inlet)
    sol_warm = MultiShaftEqualRatioSolver(process_pipelines=warm).find_solution(constraint, inlet)

    assert sol_cool.success and sol_warm.success

    speeds_cool = [c.value.speed for c in sol_cool.configuration if isinstance(c.value, SpeedConfiguration)]
    speeds_warm = [c.value.speed for c in sol_warm.configuration if isinstance(c.value, SpeedConfiguration)]

    assert speeds_cool[0] != speeds_warm[0]
    assert speeds_cool[1] != speeds_warm[1]


def test_empty_pipelines(stream_factory):
    solver = MultiShaftEqualRatioSolver(process_pipelines=[])
    inlet = stream_factory(standard_rate_m3_per_day=1_500_000.0, pressure_bara=30.0, temperature_kelvin=303.15)

    solution = solver.find_solution(FloatConstraint(270.0, abs_tol=5.0), inlet)

    assert solution.success
    assert solution.configuration == []
    assert solution.failure_event is None


def test_single_pipeline_hits_exact_target(stream_factory, pipeline_kwargs):
    """With one pipeline the target is the exact constraint (no intermediate splitting)."""
    pipeline = make_process_pipeline(min_rate=200, max_rate=5000, **pipeline_kwargs)
    solver = MultiShaftEqualRatioSolver(process_pipelines=[pipeline])
    inlet = stream_factory(standard_rate_m3_per_day=1_500_000.0, pressure_bara=30.0, temperature_kelvin=303.15)

    solution = solver.find_solution(FloatConstraint(60.0, abs_tol=0.5), inlet)

    assert solution.success
    pipeline.runner.apply_configurations(solution.configuration)
    outlet = pipeline.runner.run(inlet)
    assert outlet.pressure_bara == pytest.approx(60.0, abs=0.5)


def test_two_pipeline_intermediate_target_is_geometric_mean(stream_factory, pipeline_kwargs):
    """With two pipelines the intermediate target should be sqrt(P_in * P_out)."""
    pipelines = [
        make_process_pipeline(min_rate=200, max_rate=5000, **pipeline_kwargs),
        make_process_pipeline(min_rate=150, max_rate=3500, **pipeline_kwargs),
    ]
    solver = MultiShaftEqualRatioSolver(process_pipelines=pipelines)
    inlet = stream_factory(standard_rate_m3_per_day=1_500_000.0, pressure_bara=30.0, temperature_kelvin=303.15)

    solution = solver.find_solution(FloatConstraint(120.0, abs_tol=1.0), inlet)

    assert solution.success
    # First pipeline should target sqrt(30 * 120) ≈ 60 bara
    intermediate = pipelines[0].runner.run(inlet)
    assert intermediate.pressure_bara == pytest.approx(60.0, abs=1.0)
