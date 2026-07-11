"""Anti-surge controller behavior (real fluids).

Ported from process_solver/anti_surge + the recirculation-solver integration
cases, plus new suspension-rule tests.
"""

from __future__ import annotations

from libecalc.process_concept_draft_v3 import (
    CommonASVLoop,
    CompressorStage,
    Param,
    Shaft,
    chain,
)
from libecalc.process_concept_draft_v3.control import evaluate_with_surge_control
from libecalc.process_concept_draft_v3.system import ViolationKind

from .conftest import INLET_TEMPERATURE_KELVIN


def _below_surge_feed(stage, make_stream, fluid_service, speed, factor=0.4, pressure=30.0, temperature=288.15):
    probe = make_stream(1.0, pressure, temperature)
    compressor_inlet = stage.compressor_inlet(probe, 0.0, fluid_service)
    bounds = stage.standard_rate_range(compressor_inlet, speed, fluid_service)
    return make_stream(bounds.min * factor, pressure, temperature)


def _two_individual_stages(fluid_service, variable_speed_chart):
    from .conftest import make_variable_speed_chart

    shaft = Shaft()
    stage1 = CompressorStage(chart=variable_speed_chart, shaft=shaft, inlet_temperature_kelvin=INLET_TEMPERATURE_KELVIN)
    stage2 = CompressorStage(
        chart=make_variable_speed_chart(), shaft=shaft, inlet_temperature_kelvin=INLET_TEMPERATURE_KELVIN
    )
    system = chain("feed", stage1, stage2, fluid_service=fluid_service)
    return system, shaft, stage1, stage2


def _two_common_stages(fluid_service, variable_speed_chart):
    from .conftest import make_variable_speed_chart

    shaft = Shaft()
    loop = CommonASVLoop()
    stage1 = CompressorStage(chart=variable_speed_chart, shaft=shaft, inlet_temperature_kelvin=INLET_TEMPERATURE_KELVIN)
    stage2 = CompressorStage(
        chart=make_variable_speed_chart(), shaft=shaft, inlet_temperature_kelvin=INLET_TEMPERATURE_KELVIN
    )
    system = chain("feed", loop.inlet, stage1, stage2, loop.outlet, fluid_service=fluid_service)
    return system, shaft, loop, stage1, stage2


# --------------------------------------------------------------- stonewall (no recirc)


def test_above_stonewall_returns_rate_too_high(fluid_service, make_stream, variable_speed_chart):
    shaft = Shaft()
    stage = CompressorStage(chart=variable_speed_chart, shaft=shaft, inlet_temperature_kelvin=INLET_TEMPERATURE_KELVIN)
    system = chain("feed", stage, fluid_service=fluid_service)
    feed = make_stream(1e12, 30.0, 288.15)
    state, autos = evaluate_with_surge_control(system, {Param(shaft, "speed"): 100.0}, {"feed": feed})
    assert not state.feasible
    assert state.violation.kind is ViolationKind.RATE_TOO_HIGH
    assert all(value == 0.0 for value in autos.values())  # recirculation never attempted


# --------------------------------------------------------------- per-stage restoration


def test_per_stage_restoration_brings_stage_onto_min_flow_line(fluid_service, make_stream, variable_speed_chart):
    system, shaft, stage1, stage2 = _two_individual_stages(fluid_service, variable_speed_chart)
    speed = 75.0
    feed = _below_surge_feed(stage1, make_stream, fluid_service, speed, factor=0.4)

    uncontrolled = system.evaluate({Param(shaft, "speed"): speed}, {"feed": feed})
    assert not uncontrolled.feasible and uncontrolled.violation.kind is ViolationKind.RATE_TOO_LOW

    state, autos = evaluate_with_surge_control(system, {Param(shaft, "speed"): speed}, {"feed": feed})
    assert state.feasible
    assert autos[Param(stage1, "recirculation_rate")] > 0.0
    point = state.result(stage1)
    # On the minimum-flow line (small positive margin from the boundary nudge).
    assert point.surge_margin_m3h >= -1e-6
    assert point.surge_margin_m3h < 0.05 * (point.maximum_rate_m3h - point.minimum_rate_m3h)


# --------------------------------------------------------------- common-loop restoration


def test_common_loop_restoration_binding_stage_on_min_line(fluid_service, make_stream, variable_speed_chart):
    system, shaft, loop, stage1, stage2 = _two_common_stages(fluid_service, variable_speed_chart)
    speed = 75.0
    feed = _below_surge_feed(stage1, make_stream, fluid_service, speed, factor=0.4)

    state, autos = evaluate_with_surge_control(system, {Param(shaft, "speed"): speed}, {"feed": feed})
    assert state.feasible
    loop_rate = autos[Param(loop, "rate_sm3_per_day")]
    assert loop_rate > 0.0
    # Stage recircs are idle under the common loop.
    assert Param(stage1, "recirculation_rate") not in autos

    margins = [state.result(stage1).surge_margin_m3h, state.result(stage2).surge_margin_m3h]
    # The binding (most-starved) stage sits on its minimum-flow line.
    assert min(margins) >= -1e-6
    assert min(margins) < 25.0


# --------------------------------------------------------------- suspension rule


def test_suspension_rule_returns_infeasible(fluid_service, make_stream, variable_speed_chart):
    system, shaft, loop, stage1, stage2 = _two_common_stages(fluid_service, variable_speed_chart)
    speed = 75.0
    feed = _below_surge_feed(stage1, make_stream, fluid_service, speed, factor=0.4)
    loop_param = Param(loop, "rate_sm3_per_day")

    state, autos = evaluate_with_surge_control(
        system, {Param(shaft, "speed"): speed}, {"feed": feed}, suspended=frozenset({loop_param})
    )
    assert not state.feasible
    assert state.violation.kind is ViolationKind.RATE_TOO_LOW
    assert loop_param not in autos


def test_overriding_loop_rate_makes_feasible_with_empty_autos(fluid_service, make_stream, variable_speed_chart):
    system, shaft, loop, stage1, stage2 = _two_common_stages(fluid_service, variable_speed_chart)
    speed = 75.0
    feed = _below_surge_feed(stage1, make_stream, fluid_service, speed, factor=0.4)
    loop_param = Param(loop, "rate_sm3_per_day")

    # Discover a sufficient rate via the controller, then pin it as an override.
    _, autos = evaluate_with_surge_control(system, {Param(shaft, "speed"): speed}, {"feed": feed})
    sufficient = autos[loop_param]

    state, autos2 = evaluate_with_surge_control(
        system,
        {Param(shaft, "speed"): speed, loop_param: sufficient},
        {"feed": feed},
        suspended=frozenset({loop_param}),
    )
    assert state.feasible
    assert loop_param not in autos2


# --------------------------------------------------------------- speed dependence


def test_restoration_redecides_per_speed(fluid_service, make_stream, variable_speed_chart):
    system, shaft, stage1, stage2 = _two_individual_stages(fluid_service, variable_speed_chart)
    feed_lo_speed = 70.0
    feed_hi_speed = 90.0
    feed = _below_surge_feed(stage1, make_stream, fluid_service, feed_hi_speed, factor=0.5)

    _, autos_lo = evaluate_with_surge_control(system, {Param(shaft, "speed"): feed_lo_speed}, {"feed": feed})
    _, autos_hi = evaluate_with_surge_control(system, {Param(shaft, "speed"): feed_hi_speed}, {"feed": feed})

    # Higher speed lifts the minimum-flow line, so it needs more recirculation.
    assert autos_hi[Param(stage1, "recirculation_rate")] > autos_lo[Param(stage1, "recirculation_rate")]
