"""Ported legacy-domain behavior: stage-compatibility validation and splitter accounting."""

from __future__ import annotations

import pytest

from libecalc.domain.process.value_objects.chart import ChartCurve
from libecalc.process_concept_draft_v3 import CompressorStage, Shaft, Splitter, chain
from libecalc.process_concept_draft_v3.solver import speed_bounds
from libecalc.process_concept_draft_v3.units import OUT, SIDE_OUT
from libecalc.testing.chart_data_factory import ChartDataFactory

from .conftest import INLET_TEMPERATURE_KELVIN, make_variable_speed_chart


def _chart_with_speeds(speeds):
    curves = [
        ChartCurve(
            speed_rpm=speed,
            rate_actual_m3_hour=[500.0 * speed / 100.0, 1500.0 * speed / 100.0],
            polytropic_head_joule_per_kg=[70_000.0 * (speed / 100.0) ** 2, 50_000.0 * (speed / 100.0) ** 2],
            efficiency_fraction=[0.75, 0.75],
        )
        for speed in speeds
    ]
    return ChartDataFactory.from_curves(curves, control_margin=0.0)


# ----------------------------------------------------- stage-compatibility validation


def test_known_compatible_stages_resolve_speed_bounds(fluid_service):
    shaft = Shaft()
    stage1 = CompressorStage(
        chart=make_variable_speed_chart(), shaft=shaft, inlet_temperature_kelvin=INLET_TEMPERATURE_KELVIN
    )
    stage2 = CompressorStage(
        chart=make_variable_speed_chart(), shaft=shaft, inlet_temperature_kelvin=INLET_TEMPERATURE_KELVIN
    )
    system = chain("feed", stage1, stage2, fluid_service=fluid_service)
    bounds = speed_bounds(system, shaft)
    assert bounds.lower < bounds.upper


def test_overlapping_ranges_resolve_to_intersection(fluid_service):
    shaft = Shaft()
    stage1 = CompressorStage(
        chart=_chart_with_speeds([60.0, 80.0, 100.0]), shaft=shaft, inlet_temperature_kelvin=INLET_TEMPERATURE_KELVIN
    )
    stage2 = CompressorStage(
        chart=_chart_with_speeds([80.0, 100.0, 120.0]), shaft=shaft, inlet_temperature_kelvin=INLET_TEMPERATURE_KELVIN
    )
    system = chain("feed", stage1, stage2, fluid_service=fluid_service)
    bounds = speed_bounds(system, shaft)
    assert bounds.lower == pytest.approx(80.0)
    assert bounds.upper == pytest.approx(100.0)


def test_incompatible_disjoint_ranges_raise(fluid_service):
    shaft = Shaft()
    stage1 = CompressorStage(
        chart=_chart_with_speeds([60.0, 80.0, 100.0]), shaft=shaft, inlet_temperature_kelvin=INLET_TEMPERATURE_KELVIN
    )
    stage2 = CompressorStage(
        chart=_chart_with_speeds([200.0, 250.0, 300.0]), shaft=shaft, inlet_temperature_kelvin=INLET_TEMPERATURE_KELVIN
    )
    system = chain("feed", stage1, stage2, fluid_service=fluid_service)
    with pytest.raises(ValueError, match="empty speed interval|disjoint"):
        speed_bounds(system, shaft)


# ----------------------------------------------------- splitter multi-offtake accounting


def test_two_splitters_in_series_accounting(fluid_service, make_stream):
    split1 = Splitter(offtake_rate_sm3_per_day=60_000.0)
    split2 = Splitter(offtake_rate_sm3_per_day=40_000.0)
    system = chain("feed", split1, split2, fluid_service=fluid_service)
    feed = make_stream(500_000.0, 30.0, 300.0)
    state = system.evaluate({}, {"feed": feed})

    assert state.out(split1, SIDE_OUT).standard_rate_sm3_per_day == pytest.approx(60_000.0, rel=1e-6)
    assert state.out(split1, OUT).standard_rate_sm3_per_day == pytest.approx(440_000.0, rel=1e-6)
    assert state.out(split2, SIDE_OUT).standard_rate_sm3_per_day == pytest.approx(40_000.0, rel=1e-6)
    assert state.out(split2, OUT).standard_rate_sm3_per_day == pytest.approx(400_000.0, rel=1e-6)
