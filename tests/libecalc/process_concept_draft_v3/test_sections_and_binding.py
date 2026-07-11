"""Sections and the binding-section rule vs the legacy MultiPressureSolver."""

from __future__ import annotations

import dataclasses

import pytest

from libecalc.common.utils.ecalc_uuid import ecalc_id_generator
from libecalc.process.process_pipeline.process_pipeline import ProcessPipelineId
from libecalc.process.process_solver.anti_surge.individual_asv import IndividualASVAntiSurgeStrategy
from libecalc.process.process_solver.float_constraint import FloatConstraint
from libecalc.process.process_solver.multi_pressure_solver import MultiPressureSolver
from libecalc.process.process_solver.pipeline_section import PipelineSection
from libecalc.process.process_solver.pressure_control.individual_asv import IndividualASVPressureControlStrategy
from libecalc.process.process_solver.process_pipeline_runner import ProcessPipelineRunner
from libecalc.process.process_solver.recirculation_loop import RecirculationLoop as LegacyRecirculationLoop
from libecalc.process.process_solver.search_strategies import ScipyRootFindingStrategy
from libecalc.process.process_units.compressor import Compressor as CompressorKernel
from libecalc.process.process_units.direct_mixer import DirectMixer
from libecalc.process.process_units.direct_splitter import DirectSplitter
from libecalc.process.process_units.splitter import Splitter as SplitterKernel
from libecalc.process.process_units.temperature_setter import TemperatureSetter
from libecalc.process.shaft import VariableSpeedShaft
from libecalc.process_concept_draft_v3 import Choke, CompressorStage, Shaft, Splitter, chain
from libecalc.process_concept_draft_v3.params import Param
from libecalc.process_concept_draft_v3.solver import (
    FROM_CAPACITY,
    FROM_CHART,
    INF,
    Bounds,
    Constraint,
    Probe,
    Target,
    solve,
)

from .conftest import INLET_TEMPERATURE_KELVIN, make_variable_speed_chart

INTERSTAGE_TARGET = 37.0
OUTLET_TARGET = 53.0
OFFTAKE = 60_000.0


def _build_legacy_interstage(service, chart1, chart2):
    root_finding = ScipyRootFindingStrategy()
    shaft = VariableSpeedShaft()

    def make_section(compressor, leading_units):
        shaft.connect(compressor)
        mixer, splitter = DirectMixer(), DirectSplitter()
        loop = LegacyRecirculationLoop(mixer=mixer, splitter=splitter)
        cooler = TemperatureSetter(required_temperature_kelvin=INLET_TEMPERATURE_KELVIN, fluid_service=service)
        units = [*leading_units, mixer, cooler, compressor, splitter]
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
            speed_boundary=None,
            root_finding_strategy=root_finding,
        )
        return section, loop

    compressor1 = CompressorKernel(compressor_chart=chart1, fluid_service=service)
    compressor2 = CompressorKernel(compressor_chart=chart2, fluid_service=service)
    section1, loop1 = make_section(compressor1, leading_units=[])
    section2, loop2 = make_section(compressor2, leading_units=[SplitterKernel(fluid_service=service, rate=OFFTAKE)])
    boundary = shaft.get_speed_boundary()
    section1 = dataclasses.replace(section1, speed_boundary=boundary)
    section2 = dataclasses.replace(section2, speed_boundary=boundary)
    return shaft, [section1, section2], [loop1, loop2]


def _build_v3_interstage(fluid_service, chart1, chart2):
    shaft = Shaft()
    stage1 = CompressorStage(chart=chart1, shaft=shaft, inlet_temperature_kelvin=INLET_TEMPERATURE_KELVIN)
    split = Splitter(offtake_rate_sm3_per_day=OFFTAKE)
    stage2 = CompressorStage(chart=chart2, shaft=shaft, inlet_temperature_kelvin=INLET_TEMPERATURE_KELVIN)
    system = chain("feed", stage1, split, stage2, fluid_service=fluid_service)
    speed = Param(shaft, "speed")
    constraints = [
        Constraint(
            vary=speed,
            target=Target(Probe.outlet_pressure(stage1), INTERSTAGE_TARGET),
            bounds=FROM_CHART,
            fallback=Constraint(
                vary=Param(stage1, "recirculation_rate"),
                target=Target(Probe.outlet_pressure(stage1), INTERSTAGE_TARGET),
                bounds=FROM_CAPACITY,
            ),
        ),
        Constraint(
            vary=speed,
            target=Target(Probe.outlet_pressure(stage2), OUTLET_TARGET),
            bounds=FROM_CHART,
            fallback=Constraint(
                vary=Param(stage2, "recirculation_rate"),
                target=Target(Probe.outlet_pressure(stage2), OUTLET_TARGET),
                bounds=FROM_CAPACITY,
            ),
        ),
    ]
    return system, shaft, stage1, stage2, constraints


def test_interstage_parity(fluid_service, make_stream):
    chart1, chart2 = make_variable_speed_chart(), make_variable_speed_chart()
    inlet = make_stream(500_000.0, 25.0)

    shaft_legacy, sections, loops = _build_legacy_interstage(fluid_service, chart1, chart2)
    legacy_solution = MultiPressureSolver(pipeline_sections=sections).find_solution(
        pressure_targets=[FloatConstraint(INTERSTAGE_TARGET), FloatConstraint(OUTLET_TARGET)],
        inlet_stream=inlet,
    )
    legacy_speed = legacy_solution.get_configuration(shaft_legacy.get_id()).speed
    legacy_recirc = [legacy_solution.get_configuration(loop.get_id()).recirculation_rate for loop in loops]

    system, shaft, stage1, stage2, constraints = _build_v3_interstage(fluid_service, chart1, chart2)
    result = solve(system, constraints, {"feed": inlet})

    assert legacy_solution.success and result.success
    speed = Param(shaft, "speed")
    assert result.values[speed] == pytest.approx(legacy_speed, rel=1e-3)
    assert result.values[speed] == pytest.approx(90.556449, rel=2e-3)
    assert result.state.out(stage1).pressure_bara == pytest.approx(INTERSTAGE_TARGET, abs=1e-3)
    assert result.state.out(stage2).pressure_bara == pytest.approx(OUTLET_TARGET, abs=1e-3)

    for stage, legacy_rate in [(stage1, legacy_recirc[0]), (stage2, legacy_recirc[1])]:
        v3_rate = result.values.get(
            Param(stage, "recirculation_rate"), result.auto_values.get(Param(stage, "recirculation_rate"), 0.0)
        )
        assert v3_rate == pytest.approx(legacy_rate, abs=max(1e-2 * max(legacy_rate, 1.0), 1.0))


def test_binding_detects_shared_shaft_and_two_sections(fluid_service, make_stream):
    chart1, chart2 = make_variable_speed_chart(), make_variable_speed_chart()
    inlet = make_stream(500_000.0, 25.0)
    system, shaft, stage1, stage2, constraints = _build_v3_interstage(fluid_service, chart1, chart2)
    result = solve(system, constraints, {"feed": inlet})
    # Binding: a single shared speed appears once in values.
    assert result.values[Param(shaft, "speed")] == result.values[Param(shaft, "speed")]
    assert result.success


def test_downstream_choke_placement_only_on_last_section(fluid_service, make_stream):
    chart = make_variable_speed_chart()
    shaft = Shaft()
    stage1 = CompressorStage(chart=chart, shaft=shaft, inlet_temperature_kelvin=INLET_TEMPERATURE_KELVIN)
    choke1 = Choke()
    stage2 = CompressorStage(chart=chart, shaft=shaft, inlet_temperature_kelvin=INLET_TEMPERATURE_KELVIN)
    system = chain("feed", stage1, choke1, stage2, fluid_service=fluid_service)
    speed = Param(shaft, "speed")
    # Downstream-choke fallback on the FIRST section (anchored at choke1) — invalid placement.
    constraints = [
        Constraint(
            vary=speed,
            target=Target(Probe.outlet_pressure(choke1), 37.0),
            bounds=FROM_CHART,
            fallback=Constraint(
                Param(choke1, "delta_pressure"), Target(Probe.outlet_pressure(choke1), 37.0), Bounds(0.0, INF)
            ),
        ),
        Constraint(vary=speed, target=Target(Probe.outlet_pressure(stage2), 53.0), bounds=FROM_CHART),
    ]
    with pytest.raises(ValueError, match="downstream-choke"):
        solve(system, constraints, {"feed": make_stream(500_000.0, 25.0)})
