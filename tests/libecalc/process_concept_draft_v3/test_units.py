"""Unit-behavior tests (ported from tests/libecalc/process/process_units/).

Compressor behavior is exercised through ``CompressorStage`` with the cooler
disabled; primitives are exercised directly. All assertions mirror the existing
kernel tests' expectations.
"""

from __future__ import annotations

import pytest

from libecalc.process_concept_draft_v3 import (
    Choke,
    CommonASVLoop,
    CompressorStage,
    Cooler,
    LiquidRemover,
    Mixer,
    Param,
    Shaft,
    Splitter,
    chain,
)
from libecalc.process_concept_draft_v3.units import IN, OUT, SIDE_IN, SIDE_OUT, Ctx, Overrides, add_rate, remove_rate


def _ctx(fluid_service, overrides=None):
    return Ctx(fluid_service, Overrides(overrides or {}))


def _midpoint_stream(stage, make_stream, fluid_service, speed, pressure_bara=30.0, temperature_kelvin=300.0):
    placeholder = make_stream(1.0, pressure_bara, temperature_kelvin)
    bounds = stage.standard_rate_range(placeholder, speed, fluid_service)
    rate = (bounds.min + bounds.max) / 2
    return make_stream(rate, pressure_bara, temperature_kelvin)


# --------------------------------------------------------------------- compressor


class TestCompressorStageBehavior:
    def test_outlet_pressure_higher_than_inlet(self, fluid_service, make_stream, variable_speed_chart):
        shaft = Shaft()
        stage = CompressorStage(chart=variable_speed_chart, shaft=shaft, inlet_temperature_kelvin=None)
        system = chain("feed", stage, fluid_service=fluid_service)
        inlet = _midpoint_stream(stage, make_stream, fluid_service, speed=80.0)
        state = system.evaluate({Param(shaft, "speed"): 80.0}, {"feed": inlet})
        assert state.feasible
        assert state.out(stage).pressure_bara > inlet.pressure_bara

    def test_higher_speed_gives_higher_outlet_pressure(self, fluid_service, make_stream, variable_speed_chart):
        shaft = Shaft()
        stage = CompressorStage(chart=variable_speed_chart, shaft=shaft, inlet_temperature_kelvin=None)
        system = chain("feed", stage, fluid_service=fluid_service)

        inlet_low = _midpoint_stream(stage, make_stream, fluid_service, speed=66.0)
        out_low = system.evaluate({Param(shaft, "speed"): 66.0}, {"feed": inlet_low}).out(stage)
        inlet_high = _midpoint_stream(stage, make_stream, fluid_service, speed=95.0)
        out_high = system.evaluate({Param(shaft, "speed"): 95.0}, {"feed": inlet_high}).out(stage)

        assert out_high.pressure_bara > out_low.pressure_bara

    def test_standard_rate_conserved_across_stage(self, fluid_service, make_stream, variable_speed_chart):
        shaft = Shaft()
        stage = CompressorStage(chart=variable_speed_chart, shaft=shaft, inlet_temperature_kelvin=None)
        system = chain("feed", stage, fluid_service=fluid_service)
        inlet = _midpoint_stream(stage, make_stream, fluid_service, speed=80.0)
        outlet = system.evaluate({Param(shaft, "speed"): 80.0}, {"feed": inlet}).out(stage)
        assert outlet.standard_rate_sm3_per_day == pytest.approx(inlet.standard_rate_sm3_per_day, rel=1e-6)

    def test_rate_too_low_raised_as_violation(self, fluid_service, make_stream, variable_speed_chart):
        shaft = Shaft()
        stage = CompressorStage(chart=variable_speed_chart, shaft=shaft, inlet_temperature_kelvin=None)
        system = chain("feed", stage, fluid_service=fluid_service)
        tiny = make_stream(1.0, 30.0, 300.0)
        state = system.evaluate({Param(shaft, "speed"): 60.0}, {"feed": tiny})
        assert not state.feasible
        assert state.violation.unit is stage
        assert state.violation.kind.value == "rate_too_low"

    def test_rate_too_high_raised_as_violation(self, fluid_service, make_stream, variable_speed_chart):
        shaft = Shaft()
        stage = CompressorStage(chart=variable_speed_chart, shaft=shaft, inlet_temperature_kelvin=None)
        system = chain("feed", stage, fluid_service=fluid_service)
        huge = make_stream(1e12, 30.0, 300.0)
        state = system.evaluate({Param(shaft, "speed"): 100.0}, {"feed": huge})
        assert not state.feasible
        assert state.violation.kind.value == "rate_too_high"

    def test_recirculation_range_zero_above_surge(self, fluid_service, make_stream, variable_speed_chart):
        shaft = Shaft()
        stage = CompressorStage(chart=variable_speed_chart, shaft=shaft, inlet_temperature_kelvin=None)
        inlet = _midpoint_stream(stage, make_stream, fluid_service, speed=80.0)
        boundary = stage.recirculation_range(inlet, 80.0, fluid_service)
        assert boundary.min == pytest.approx(0.0)

    def test_recirculation_range_positive_below_surge(self, fluid_service, make_stream, variable_speed_chart):
        shaft = Shaft()
        stage = CompressorStage(chart=variable_speed_chart, shaft=shaft, inlet_temperature_kelvin=None)
        placeholder = make_stream(1.0, 30.0, 300.0)
        bounds = stage.standard_rate_range(placeholder, 90.0, fluid_service)
        inlet = make_stream(bounds.min * 0.5, 30.0, 300.0)
        boundary = stage.recirculation_range(inlet, 90.0, fluid_service)
        assert boundary.min > 0.0

    def test_operating_point_recorded(self, fluid_service, make_stream, variable_speed_chart):
        shaft = Shaft()
        stage = CompressorStage(chart=variable_speed_chart, shaft=shaft, inlet_temperature_kelvin=None)
        system = chain("feed", stage, fluid_service=fluid_service)
        inlet = _midpoint_stream(stage, make_stream, fluid_service, speed=80.0)
        state = system.evaluate({Param(shaft, "speed"): 80.0}, {"feed": inlet})
        point = state.result(stage)
        assert point.minimum_rate_m3h < point.actual_rate_m3h < point.maximum_rate_m3h
        assert point.power_mw > 0.0
        assert point.surge_margin_m3h > 0.0


# --------------------------------------------------------------------- choke


def test_choke_subtracts_pressure(fluid_service, make_stream):
    choke = Choke()
    system = chain("feed", choke, fluid_service=fluid_service)
    inlet = make_stream(100_000.0, 50.0, 300.0)
    out = system.evaluate({Param(choke, "delta_pressure"): 3.0}, {"feed": inlet}).out(choke)
    assert out.pressure_bara == pytest.approx(47.0)


def test_choke_zero_is_passthrough(fluid_service, make_stream):
    choke = Choke()
    system = chain("feed", choke, fluid_service=fluid_service)
    inlet = make_stream(100_000.0, 50.0, 300.0)
    out = system.evaluate({}, {"feed": inlet}).out(choke)
    assert out.pressure_bara == pytest.approx(50.0)


def test_choke_to_negative_pressure_is_violation(fluid_service, make_stream):
    choke = Choke()
    system = chain("feed", choke, fluid_service=fluid_service)
    inlet = make_stream(100_000.0, 5.0, 300.0)
    state = system.evaluate({Param(choke, "delta_pressure"): 10.0}, {"feed": inlet})
    assert not state.feasible
    assert state.violation.kind.value == "other"


# --------------------------------------------------------------------- cooler


def test_cooler_sets_outlet_temperature(fluid_service, make_stream):
    cooler = Cooler(outlet_temperature_kelvin=310.0)
    system = chain("feed", cooler, fluid_service=fluid_service)
    inlet = make_stream(100_000.0, 30.0, 350.0)
    out = system.evaluate({}, {"feed": inlet}).out(cooler)
    assert out.temperature_kelvin == pytest.approx(310.0)


# --------------------------------------------------------------------- splitter / mixer


def test_splitter_offtake_and_remainder(fluid_service, make_stream):
    splitter = Splitter(offtake_rate_sm3_per_day=60_000.0)
    system = chain("feed", splitter, fluid_service=fluid_service)
    inlet = make_stream(500_000.0, 30.0, 300.0)
    state = system.evaluate({}, {"feed": inlet})
    assert state.out(splitter, OUT).standard_rate_sm3_per_day == pytest.approx(440_000.0, rel=1e-6)
    assert state.out(splitter, SIDE_OUT).standard_rate_sm3_per_day == pytest.approx(60_000.0, rel=1e-6)


def test_mixer_adds_side_stream_mass(fluid_service, make_stream):
    mixer = Mixer()
    side = make_stream(40_000.0, 30.0, 300.0)
    main = make_stream(200_000.0, 30.0, 300.0)
    system = chain(mixer, fluid_service=fluid_service)
    system.feed_into(mixer, "main", IN)
    system.feed_into(mixer, "side", SIDE_IN)
    out = system.evaluate({}, {"main": main, "side": side}).out(mixer)
    assert out.mass_rate_kg_per_h == pytest.approx(main.mass_rate_kg_per_h + side.mass_rate_kg_per_h, rel=1e-9)


# --------------------------------------------------------------------- liquid remover


def test_liquid_remover_passthrough_when_pure_vapor(fluid_service, make_stream):
    remover = LiquidRemover()
    system = chain("feed", remover, fluid_service=fluid_service)
    inlet = make_stream(100_000.0, 30.0, 320.0)
    out = system.evaluate({}, {"feed": inlet}).out(remover)
    assert out.mass_rate_kg_per_h == pytest.approx(inlet.mass_rate_kg_per_h, rel=1e-9)


def test_stage_remove_liquid_flag(fluid_service, make_stream, variable_speed_chart):
    shaft = Shaft()
    stage = CompressorStage(chart=variable_speed_chart, shaft=shaft, inlet_temperature_kelvin=None, remove_liquid=True)
    system = chain("feed", stage, fluid_service=fluid_service)
    inlet = _midpoint_stream(stage, make_stream, fluid_service, speed=80.0)
    state = system.evaluate({Param(shaft, "speed"): 80.0}, {"feed": inlet})
    assert state.feasible


# --------------------------------------------------------------------- rate modifier (recirculation parameter)


def test_add_then_remove_rate_is_identity(fluid_service, make_stream):
    stream = make_stream(100_000.0, 30.0, 300.0)
    middle = add_rate(stream, 50_000.0)
    end = remove_rate(middle, 50_000.0)
    assert middle.mass_rate_kg_per_h > stream.mass_rate_kg_per_h
    assert end.mass_rate_kg_per_h == pytest.approx(stream.mass_rate_kg_per_h, rel=1e-12)


def test_stage_recirculation_preserves_standard_rate(fluid_service, make_stream, variable_speed_chart):
    """Recirculation is rate-only: outlet standard rate equals inlet, composition preserved."""
    shaft = Shaft()
    stage = CompressorStage(chart=variable_speed_chart, shaft=shaft, inlet_temperature_kelvin=None)
    system = chain("feed", stage, fluid_service=fluid_service)
    inlet = _midpoint_stream(stage, make_stream, fluid_service, speed=80.0)
    out = system.evaluate(
        {Param(shaft, "speed"): 80.0, Param(stage, "recirculation_rate"): 30_000.0}, {"feed": inlet}
    ).out(stage)
    assert out.standard_rate_sm3_per_day == pytest.approx(inlet.standard_rate_sm3_per_day, rel=1e-6)


def test_loop_add_remove_views_share_rate(fluid_service, make_stream, variable_speed_chart):
    shaft = Shaft()
    stage = CompressorStage(chart=variable_speed_chart, shaft=shaft, inlet_temperature_kelvin=None)
    loop = CommonASVLoop()
    system = chain("feed", loop.inlet, stage, loop.outlet, fluid_service=fluid_service)
    inlet = _midpoint_stream(stage, make_stream, fluid_service, speed=80.0)
    out = system.evaluate(
        {Param(shaft, "speed"): 80.0, Param(loop, "rate_sm3_per_day"): 25_000.0}, {"feed": inlet}
    ).out(loop.outlet)
    assert out.standard_rate_sm3_per_day == pytest.approx(inlet.standard_rate_sm3_per_day, rel=1e-6)
