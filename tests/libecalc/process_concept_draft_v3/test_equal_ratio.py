"""Equal-ratio target helper for independent-shaft (multi-shaft) trains."""

from __future__ import annotations

import pytest

from libecalc.process_concept_draft_v3 import CompressorStage, Shaft, chain
from libecalc.process_concept_draft_v3.params import Param
from libecalc.process_concept_draft_v3.solver import (
    FROM_CAPACITY,
    FROM_CHART,
    Constraint,
    Probe,
    Target,
    equal_ratio_targets,
    solve,
)

from .conftest import INLET_TEMPERATURE_KELVIN, make_variable_speed_chart


def test_equal_ratio_targets_split():
    targets = equal_ratio_targets(total_target=53.0, inlet_pressure=25.0, n_sections=2)
    assert len(targets) == 2
    ratio = (53.0 / 25.0) ** 0.5
    assert targets[0] == pytest.approx(25.0 * ratio)
    assert targets[1] == pytest.approx(53.0)  # the last is exactly the total


def test_equal_ratio_targets_single():
    targets = equal_ratio_targets(total_target=40.0, inlet_pressure=25.0, n_sections=1)
    assert targets == [40.0]


def test_equal_ratio_multi_shaft_solve(fluid_service, make_stream):
    chart1, chart2 = make_variable_speed_chart(), make_variable_speed_chart()
    inlet = make_stream(500_000.0, 25.0)
    total_target = 53.0
    section_targets = equal_ratio_targets(total_target, inlet.pressure_bara, 2)

    shaft_a, shaft_b = Shaft(), Shaft()
    stage1 = CompressorStage(chart=chart1, shaft=shaft_a, inlet_temperature_kelvin=INLET_TEMPERATURE_KELVIN)
    stage2 = CompressorStage(chart=chart2, shaft=shaft_b, inlet_temperature_kelvin=INLET_TEMPERATURE_KELVIN)
    system = chain("feed", stage1, stage2, fluid_service=fluid_service)
    constraints = [
        Constraint(
            vary=Param(shaft_a, "speed"),
            target=Target(Probe.outlet_pressure(stage1), section_targets[0]),
            bounds=FROM_CHART,
            fallback=Constraint(
                Param(stage1, "recirculation_rate"),
                Target(Probe.outlet_pressure(stage1), section_targets[0]),
                FROM_CAPACITY,
            ),
        ),
        Constraint(
            vary=Param(shaft_b, "speed"),
            target=Target(Probe.outlet_pressure(stage2), section_targets[1]),
            bounds=FROM_CHART,
            fallback=Constraint(
                Param(stage2, "recirculation_rate"),
                Target(Probe.outlet_pressure(stage2), section_targets[1]),
                FROM_CAPACITY,
            ),
        ),
    ]
    result = solve(system, constraints, {"feed": inlet})
    assert result.success
    assert result.state.out(stage1).pressure_bara == pytest.approx(section_targets[0], abs=1e-3)
    assert result.state.out(stage2).pressure_bara == pytest.approx(total_target, abs=1e-3)
