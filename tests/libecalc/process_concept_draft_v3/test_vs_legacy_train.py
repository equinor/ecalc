"""v3 vs the legacy CompressorTrainCommonShaft domain train (direct end-to-end parity).

These close the "vs-legacy-train" gap: rather than re-asserting transitively through the
new-solver components, they compare v3's outlet stream directly against the legacy
compressor-train engine for the common-ASV and individual-ASV modes. The legacy train is
built with the inherited ``compressor_stage_factory`` fixture (``tests/libecalc/conftest.py``).
"""

from __future__ import annotations

import pytest

from libecalc.common.fixed_speed_pressure_control import FixedSpeedPressureControl
from libecalc.domain.process.compressor.core.train.compressor_train_common_shaft import CompressorTrainCommonShaft
from libecalc.domain.process.compressor.core.train.train_evaluation_input import CompressorTrainEvaluationInput
from libecalc.process.shaft import VariableSpeedShaft
from libecalc.process_concept_draft_v3.solver import solve

from .conftest import INLET_TEMPERATURE_KELVIN, build_v3_system, make_constraint, make_variable_speed_chart


def _legacy_common_shaft_outlet(
    fluid_service, fluid_model, charts, pressure_control, suction_pressure, discharge_pressure, rate, stage_factory
):
    shaft = VariableSpeedShaft()
    stages = [
        stage_factory(
            compressor_chart_data=chart,
            shaft=shaft,
            inlet_temperature_kelvin=INLET_TEMPERATURE_KELVIN,
            remove_liquid_after_cooling=True,
        )
        for chart in charts
    ]
    train = CompressorTrainCommonShaft(
        shaft=shaft,
        fluid_service=fluid_service,
        energy_usage_adjustment_constant=0,
        energy_usage_adjustment_factor=1,
        stages=stages,
        pressure_control=pressure_control,
        calculate_max_rate=False,
    )
    train._fluid_model = [fluid_model]
    result = train.evaluate_given_constraints(
        CompressorTrainEvaluationInput(
            suction_pressure=suction_pressure,
            discharge_pressure=discharge_pressure,
            rates=[rate],
        )
    )
    return result, shaft


@pytest.mark.parametrize(
    ("mode", "legacy_control"),
    [
        ("COMMON_ASV", FixedSpeedPressureControl.COMMON_ASV),
        ("INDIVIDUAL_ASV_RATE", FixedSpeedPressureControl.INDIVIDUAL_ASV_RATE),
        ("INDIVIDUAL_ASV_PRESSURE", FixedSpeedPressureControl.INDIVIDUAL_ASV_PRESSURE),
    ],
)
@pytest.mark.parametrize("target", [40.0, 50.0])
def test_two_stage_train_vs_legacy_common_shaft(
    fluid_service, make_stream, medium_fluid_model, compressor_stage_factory, mode, legacy_control, target
):
    suction = 25.0
    rate = 500_000.0
    charts = [make_variable_speed_chart(), make_variable_speed_chart()]
    feed = make_stream(rate, suction)

    legacy_result, _ = _legacy_common_shaft_outlet(
        fluid_service, medium_fluid_model, charts, legacy_control, suction, target, rate, compressor_stage_factory
    )

    built = build_v3_system(mode, charts, fluid_service, remove_liquid=True)
    result = solve(built.system, [make_constraint(built, mode, target)], {"feed": feed})

    legacy_valid = bool(legacy_result.is_valid)
    assert result.success == legacy_valid
    if result.success and legacy_valid:
        new_outlet = result.state.out(built.target_unit)
        # Same gas reaching the same target pressure -> same outlet thermodynamic state.
        assert new_outlet.pressure_bara == pytest.approx(legacy_result.outlet_stream.pressure_bara, rel=1e-3)
        assert new_outlet.density == pytest.approx(legacy_result.outlet_stream.density, rel=5e-3)
