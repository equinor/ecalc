"""System evaluation: forward parity vs the existing kernels, violations as data,
overrides purity, and construction validation."""

from __future__ import annotations

import pytest

from libecalc.process.process_solver.process_pipeline_runner import propagate_stream_many
from libecalc.process.process_units.choke import Choke as ChokeKernel
from libecalc.process.process_units.compressor import Compressor as CompressorKernel
from libecalc.process.process_units.mixer import Mixer as MixerKernel
from libecalc.process.process_units.splitter import Splitter as SplitterKernel
from libecalc.process.process_units.temperature_setter import TemperatureSetter
from libecalc.process_concept_draft_v3 import (
    Choke,
    CompressorStage,
    Mixer,
    Param,
    Shaft,
    Splitter,
    chain,
)
from libecalc.process_concept_draft_v3.units import IN, SIDE_IN

from .conftest import INLET_TEMPERATURE_KELVIN, make_variable_speed_chart

SPEED = 80.0
CHOKE_DP = 2.0
OFFTAKE = 60_000.0
SIDE_FEED = 40_000.0


def _build_two_stage(fluid_service):
    chart1, chart2 = make_variable_speed_chart(), make_variable_speed_chart()
    shaft = Shaft()
    stage1 = CompressorStage(chart=chart1, shaft=shaft, inlet_temperature_kelvin=INLET_TEMPERATURE_KELVIN)
    split = Splitter(offtake_rate_sm3_per_day=OFFTAKE)
    mix = Mixer()
    stage2 = CompressorStage(chart=chart2, shaft=shaft, inlet_temperature_kelvin=INLET_TEMPERATURE_KELVIN)
    choke = Choke()
    system = chain("feed", stage1, split, mix, stage2, choke, fluid_service=fluid_service)
    system.feed_into(mix, "import_gas", SIDE_IN)
    return system, shaft, stage1, stage2, choke, chart1, chart2


def test_forward_parity_with_legacy_kernels(fluid_service, make_stream):
    system, shaft, stage1, stage2, choke, chart1, chart2 = _build_two_stage(fluid_service)
    feed = make_stream(500_000.0, 25.0)
    side = make_stream(SIDE_FEED, 40.0, temperature_kelvin=300.0)

    state = system.evaluate(
        {Param(shaft, "speed"): SPEED, Param(choke, "delta_pressure"): CHOKE_DP},
        {"feed": feed, "import_gas": side},
    )
    assert state.feasible
    v3_outlet = state.out(choke)

    legacy_c1 = CompressorKernel(compressor_chart=chart1, fluid_service=fluid_service)
    legacy_c2 = CompressorKernel(compressor_chart=chart2, fluid_service=fluid_service)
    legacy_c1.set_speed(SPEED)
    legacy_c2.set_speed(SPEED)
    legacy_mixer = MixerKernel(fluid_service=fluid_service)
    legacy_mixer.set_stream(side)
    legacy_units = [
        TemperatureSetter(required_temperature_kelvin=INLET_TEMPERATURE_KELVIN, fluid_service=fluid_service),
        legacy_c1,
        SplitterKernel(fluid_service=fluid_service, rate=OFFTAKE),
        legacy_mixer,
        TemperatureSetter(required_temperature_kelvin=INLET_TEMPERATURE_KELVIN, fluid_service=fluid_service),
        legacy_c2,
        ChokeKernel(fluid_service=fluid_service, pressure_change=CHOKE_DP),
    ]
    legacy_outlet = propagate_stream_many(legacy_units, feed)

    assert v3_outlet.pressure_bara == pytest.approx(legacy_outlet.pressure_bara, abs=1e-9)
    assert v3_outlet.temperature_kelvin == pytest.approx(legacy_outlet.temperature_kelvin, abs=1e-9)
    assert v3_outlet.mass_rate_kg_per_h == pytest.approx(legacy_outlet.mass_rate_kg_per_h, abs=1e-6)


def test_violation_rate_too_low(fluid_service, make_stream, variable_speed_chart):
    shaft = Shaft()
    stage = CompressorStage(chart=variable_speed_chart, shaft=shaft, inlet_temperature_kelvin=None)
    system = chain("feed", stage, fluid_service=fluid_service)
    state = system.evaluate({Param(shaft, "speed"): 60.0}, {"feed": make_stream(1.0, 30.0, 300.0)})
    assert not state.feasible
    assert state.violation.kind.value == "rate_too_low"
    assert state.violation.unit is stage


def test_violation_rate_too_high(fluid_service, make_stream, variable_speed_chart):
    shaft = Shaft()
    stage = CompressorStage(chart=variable_speed_chart, shaft=shaft, inlet_temperature_kelvin=None)
    system = chain("feed", stage, fluid_service=fluid_service)
    state = system.evaluate({Param(shaft, "speed"): 100.0}, {"feed": make_stream(1e12, 30.0, 300.0)})
    assert not state.feasible
    assert state.violation.kind.value == "rate_too_high"


def test_violation_choke_negative(fluid_service, make_stream):
    choke = Choke()
    system = chain("feed", choke, fluid_service=fluid_service)
    state = system.evaluate({Param(choke, "delta_pressure"): 100.0}, {"feed": make_stream(100_000.0, 5.0)})
    assert not state.feasible
    assert state.violation.kind.value == "other"


def test_overrides_purity(fluid_service, make_stream, variable_speed_chart):
    shaft = Shaft()
    stage = CompressorStage(chart=variable_speed_chart, shaft=shaft, inlet_temperature_kelvin=None)
    system = chain("feed", stage, fluid_service=fluid_service)
    placeholder = make_stream(1.0, 30.0, 300.0)
    bounds = stage.standard_rate_range(placeholder, 80.0, fluid_service)
    inlet = make_stream((bounds.min + bounds.max) / 2, 30.0, 300.0)

    first = system.evaluate({Param(shaft, "speed"): 80.0}, {"feed": inlet})
    second = system.evaluate({Param(shaft, "speed"): 80.0}, {"feed": inlet})
    assert first.out(stage).pressure_bara == pytest.approx(second.out(stage).pressure_bara, abs=1e-12)

    bounds90 = stage.standard_rate_range(placeholder, 90.0, fluid_service)
    inlet90 = make_stream((bounds90.min + bounds90.max) / 2, 30.0, 300.0)
    other = system.evaluate({Param(shaft, "speed"): 90.0}, {"feed": inlet90})
    assert other.out(stage).pressure_bara != first.out(stage).pressure_bara

    # Units are unchanged after evaluate (the solver answer is the overrides map).
    assert stage.recirculation_rate == 0.0
    assert shaft.speed.__class__.__name__ == "Unset"


def test_unset_speed_raises_clear_message(fluid_service, make_stream, variable_speed_chart):
    shaft = Shaft()
    stage = CompressorStage(chart=variable_speed_chart, shaft=shaft, inlet_temperature_kelvin=None)
    system = chain("feed", stage, fluid_service=fluid_service)
    with pytest.raises(ValueError, match="UNSET"):
        system.evaluate({}, {"feed": make_stream(200_000.0, 30.0, 300.0)})


def test_unconnected_in_port_raises(fluid_service, make_stream):
    mixer = Mixer()
    system = chain(mixer, fluid_service=fluid_service)
    system.feed_into(mixer, "main", IN)  # side_in deliberately left unconnected
    with pytest.raises(ValueError):
        system.evaluate({}, {"main": make_stream(100_000.0, 30.0, 300.0)})


def test_param_nonexistent_field_raises_at_construction():
    shaft = Shaft()
    with pytest.raises(ValueError):
        Param(shaft, "nonexistent")
