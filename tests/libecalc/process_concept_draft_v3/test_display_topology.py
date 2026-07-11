"""Display-topology expansion per the frontend contract (plan §9)."""

from __future__ import annotations

from libecalc.process_concept_draft_v3 import (
    Choke,
    CommonASVLoop,
    CompressorStage,
    DisplayUnitKind,
    Shaft,
    Splitter,
    chain,
    display_topology,
)
from libecalc.process_concept_draft_v3.params import Param
from libecalc.process_concept_draft_v3.solver import (
    FROM_CAPACITY,
    FROM_CHART,
    Constraint,
    CoupledParameter,
    DistributionRule,
    Probe,
    Target,
)
from libecalc.process_concept_draft_v3.units import SIDE_OUT

from .conftest import INLET_TEMPERATURE_KELVIN, make_variable_speed_chart


def _kinds(topology):
    return [unit.kind for unit in topology.units]


def test_individual_asv_two_stage_has_per_stage_pairs(fluid_service):
    shaft = Shaft()
    stage1 = CompressorStage(
        chart=make_variable_speed_chart(), shaft=shaft, inlet_temperature_kelvin=INLET_TEMPERATURE_KELVIN
    )
    stage2 = CompressorStage(
        chart=make_variable_speed_chart(), shaft=shaft, inlet_temperature_kelvin=INLET_TEMPERATURE_KELVIN
    )
    system = chain("feed", stage1, stage2, fluid_service=fluid_service)
    coupled = CoupledParameter(
        "individual",
        (Param(stage1, "recirculation_rate"), Param(stage2, "recirculation_rate")),
        DistributionRule.BALANCED_RATE,
    )
    constraint = Constraint(
        vary=Param(shaft, "speed"),
        target=Target(Probe.outlet_pressure(stage2), 53.0),
        bounds=FROM_CHART,
        fallback=Constraint(vary=coupled, target=Target(Probe.outlet_pressure(stage2), 53.0), bounds=None),
    )
    topology = display_topology(system, [constraint])

    kinds = _kinds(topology)
    assert kinds.count(DisplayUnitKind.DIRECT_MIXER) == 2
    assert kinds.count(DisplayUnitKind.DIRECT_SPLITTER) == 2
    assert kinds.count(DisplayUnitKind.COMPRESSOR) == 2
    assert len(topology.loops) == 2


def test_common_asv_has_single_train_wide_pair(fluid_service):
    shaft = Shaft()
    loop = CommonASVLoop()
    stage1 = CompressorStage(
        chart=make_variable_speed_chart(), shaft=shaft, inlet_temperature_kelvin=INLET_TEMPERATURE_KELVIN
    )
    stage2 = CompressorStage(
        chart=make_variable_speed_chart(), shaft=shaft, inlet_temperature_kelvin=INLET_TEMPERATURE_KELVIN
    )
    system = chain("feed", loop.inlet, stage1, stage2, loop.outlet, fluid_service=fluid_service)
    constraint = Constraint(
        vary=Param(shaft, "speed"),
        target=Target(Probe.outlet_pressure(stage2), 53.0),
        bounds=FROM_CHART,
        fallback=Constraint(
            vary=Param(loop, "rate_sm3_per_day"),
            target=Target(Probe.outlet_pressure(stage2), 53.0),
            bounds=FROM_CAPACITY,
        ),
    )
    topology = display_topology(system, [constraint])

    kinds = _kinds(topology)
    # Exactly one train-wide pair; NO per-stage hardware (stages idle under the common loop).
    assert kinds.count(DisplayUnitKind.DIRECT_MIXER) == 1
    assert kinds.count(DisplayUnitKind.DIRECT_SPLITTER) == 1
    assert kinds.count(DisplayUnitKind.COMPRESSOR) == 2
    assert len(topology.loops) == 1


def test_splitter_side_branch_carries_port_one(fluid_service):
    shaft = Shaft()
    stage = CompressorStage(
        chart=make_variable_speed_chart(), shaft=shaft, inlet_temperature_kelvin=INLET_TEMPERATURE_KELVIN
    )
    splitter = Splitter(offtake_rate_sm3_per_day=50_000.0)
    sink = Choke()
    system = chain("feed", stage, splitter, fluid_service=fluid_service)
    system.connect(splitter, sink, from_port=SIDE_OUT, to_port="in")
    topology = display_topology(system)

    splitter_unit = next(u for u in topology.units if u.kind is DisplayUnitKind.SPLITTER)
    side = [c for c in topology.connections if c.from_id == splitter_unit.id and c.from_port == 1]
    assert len(side) == 1


def test_shaft_grouping(fluid_service):
    shaft = Shaft()
    stage1 = CompressorStage(
        chart=make_variable_speed_chart(), shaft=shaft, inlet_temperature_kelvin=INLET_TEMPERATURE_KELVIN
    )
    stage2 = CompressorStage(
        chart=make_variable_speed_chart(), shaft=shaft, inlet_temperature_kelvin=INLET_TEMPERATURE_KELVIN
    )
    system = chain("feed", stage1, stage2, fluid_service=fluid_service)
    topology = display_topology(system)
    assert len(topology.shafts) == 1
    assert len(topology.shafts[0].compressor_ids) == 2


def test_ids_are_deterministic(fluid_service):
    shaft = Shaft()
    stage = CompressorStage(
        chart=make_variable_speed_chart(), shaft=shaft, inlet_temperature_kelvin=INLET_TEMPERATURE_KELVIN
    )
    system = chain("feed", stage, fluid_service=fluid_service)
    first = display_topology(system)
    second = display_topology(system)
    assert [u.id for u in first.units] == [u.id for u in second.units]
    assert [(c.from_id, c.to_id) for c in first.connections] == [(c.from_id, c.to_id) for c in second.connections]


def test_display_works_without_solving(fluid_service):
    """Display is topology, not results — it must work for an unsolved system."""
    shaft = Shaft()
    stage = CompressorStage(chart=make_variable_speed_chart(), shaft=shaft, inlet_temperature_kelvin=None)
    system = chain("feed", stage, fluid_service=fluid_service)
    topology = display_topology(system)
    assert any(u.kind is DisplayUnitKind.COMPRESSOR for u in topology.units)
    # No cooler emitted when the stage has no cooler.
    assert all(u.kind is not DisplayUnitKind.TEMPERATURE_SETTER for u in topology.units)
