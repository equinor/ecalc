"""Independent shafts in series (multi-shaft) vs the legacy MultiShaftSolver."""

from __future__ import annotations

import dataclasses

import pytest

from libecalc.common.utils.ecalc_uuid import ecalc_id_generator
from libecalc.process.process_pipeline.process_pipeline import ProcessPipelineId
from libecalc.process.process_solver.anti_surge.individual_asv import IndividualASVAntiSurgeStrategy
from libecalc.process.process_solver.float_constraint import FloatConstraint
from libecalc.process.process_solver.multi_shaft_solver import MultiShaftSolver
from libecalc.process.process_solver.pipeline_section import PipelineSection
from libecalc.process.process_solver.pressure_control.individual_asv import IndividualASVPressureControlStrategy
from libecalc.process.process_solver.process_pipeline_runner import ProcessPipelineRunner
from libecalc.process.process_solver.recirculation_loop import RecirculationLoop as LegacyRecirculationLoop
from libecalc.process.process_solver.search_strategies import ScipyRootFindingStrategy
from libecalc.process.process_units.compressor import Compressor as CompressorKernel
from libecalc.process.process_units.direct_mixer import DirectMixer
from libecalc.process.process_units.direct_splitter import DirectSplitter
from libecalc.process.process_units.temperature_setter import TemperatureSetter
from libecalc.process.shaft import VariableSpeedShaft
from libecalc.process_concept_draft_v3 import CompressorStage, Shaft, chain
from libecalc.process_concept_draft_v3.params import Param
from libecalc.process_concept_draft_v3.solver import (
    FROM_CAPACITY,
    FROM_CHART,
    Constraint,
    Probe,
    Target,
    TargetDirection,
    TargetUnreachableFailure,
    solve,
)

from .conftest import INLET_TEMPERATURE_KELVIN, make_variable_speed_chart

TARGET_1 = 37.0
TARGET_2 = 53.0


def _legacy_section(service, chart, root_finding):
    shaft = VariableSpeedShaft()
    compressor = CompressorKernel(compressor_chart=chart, fluid_service=service)
    shaft.connect(compressor)
    mixer, splitter = DirectMixer(), DirectSplitter()
    loop = LegacyRecirculationLoop(mixer=mixer, splitter=splitter)
    cooler = TemperatureSetter(required_temperature_kelvin=INLET_TEMPERATURE_KELVIN, fluid_service=service)
    units = [mixer, cooler, compressor, splitter]
    runner = ProcessPipelineRunner(units=units, configuration_handlers=[shaft, loop])
    section = PipelineSection(
        shaft_id=shaft.get_id(),
        process_pipeline_id=ProcessPipelineId(ecalc_id_generator()),
        runner=runner,
        anti_surge_strategy=IndividualASVAntiSurgeStrategy(
            recirculation_loop_ids=[loop.get_id()], compressors=[compressor], simulator=runner
        ),
        pressure_control_strategy=IndividualASVPressureControlStrategy(
            simulator=runner,
            recirculation_loop_ids=[loop.get_id()],
            compressors=[compressor],
            root_finding_strategy=root_finding,
        ),
        speed_boundary=shaft.get_speed_boundary(),
        root_finding_strategy=root_finding,
    )
    return shaft, section


def _build_v3_multishaft(fluid_service, chart1, chart2):
    shaft_a, shaft_b = Shaft(), Shaft()
    stage1 = CompressorStage(chart=chart1, shaft=shaft_a, inlet_temperature_kelvin=INLET_TEMPERATURE_KELVIN)
    stage2 = CompressorStage(chart=chart2, shaft=shaft_b, inlet_temperature_kelvin=INLET_TEMPERATURE_KELVIN)
    system = chain("feed", stage1, stage2, fluid_service=fluid_service)
    constraints = [
        Constraint(
            vary=Param(shaft_a, "speed"),
            target=Target(Probe.outlet_pressure(stage1), TARGET_1),
            bounds=FROM_CHART,
            fallback=Constraint(
                Param(stage1, "recirculation_rate"), Target(Probe.outlet_pressure(stage1), TARGET_1), FROM_CAPACITY
            ),
        ),
        Constraint(
            vary=Param(shaft_b, "speed"),
            target=Target(Probe.outlet_pressure(stage2), TARGET_2),
            bounds=FROM_CHART,
            fallback=Constraint(
                Param(stage2, "recirculation_rate"), Target(Probe.outlet_pressure(stage2), TARGET_2), FROM_CAPACITY
            ),
        ),
    ]
    return system, shaft_a, shaft_b, stage1, stage2, constraints


def test_multi_shaft_parity(fluid_service, make_stream):
    chart1, chart2 = make_variable_speed_chart(), make_variable_speed_chart()
    inlet = make_stream(500_000.0, 25.0)
    root_finding = ScipyRootFindingStrategy()

    shaft1, section1 = _legacy_section(fluid_service, chart1, root_finding)
    shaft2, section2 = _legacy_section(fluid_service, chart2, root_finding)
    legacy_solution = MultiShaftSolver([section1, section2]).find_solution(
        [FloatConstraint(TARGET_1), FloatConstraint(TARGET_2)], inlet
    )
    legacy_speed1 = legacy_solution.get_configuration(shaft1.get_id()).speed
    legacy_speed2 = legacy_solution.get_configuration(shaft2.get_id()).speed

    system, shaft_a, shaft_b, stage1, stage2, constraints = _build_v3_multishaft(fluid_service, chart1, chart2)
    result = solve(system, constraints, {"feed": inlet})

    assert legacy_solution.success and result.success
    assert result.values[Param(shaft_a, "speed")] == pytest.approx(legacy_speed1, rel=1e-3)
    assert result.values[Param(shaft_b, "speed")] == pytest.approx(legacy_speed2, rel=1e-3)
    assert result.state.out(stage1).pressure_bara == pytest.approx(TARGET_1, abs=1e-3)
    assert result.state.out(stage2).pressure_bara == pytest.approx(TARGET_2, abs=1e-3)


def test_multi_shaft_distinct_speeds(fluid_service, make_stream):
    chart1, chart2 = make_variable_speed_chart(), make_variable_speed_chart()
    inlet = make_stream(500_000.0, 25.0)
    system, shaft_a, shaft_b, stage1, stage2, constraints = _build_v3_multishaft(fluid_service, chart1, chart2)
    result = solve(system, constraints, {"feed": inlet})
    assert result.success
    # Two independent shafts get their own speeds.
    assert Param(shaft_a, "speed") in result.values
    assert Param(shaft_b, "speed") in result.values


def test_multi_shaft_first_failure_propagates(fluid_service, make_stream):
    chart1, chart2 = make_variable_speed_chart(), make_variable_speed_chart()
    inlet = make_stream(500_000.0, 25.0)
    system, shaft_a, shaft_b, stage1, stage2, constraints = _build_v3_multishaft(fluid_service, chart1, chart2)
    # First section's target above max-speed capability -> MAX_BELOW failure; second still attempted.
    constraints[0] = dataclasses.replace(constraints[0], target=Target(Probe.outlet_pressure(stage1), 300.0))
    result = solve(system, constraints, {"feed": inlet})
    assert not result.success
    assert isinstance(result.failure, TargetUnreachableFailure)
    assert result.failure.direction is TargetDirection.MAX_BELOW_TARGET
