import pytest

from libecalc.domain.process.process_solver.float_constraint import FloatConstraint
from libecalc.domain.process.process_solver.pressure_control.downstream_choke import (
    DownstreamChokePressureControlStrategy,
    DownstreamChokeRunner,
)


def test_downstream_choke_strategy_baseline_below_target_does_not_choke(
    simple_process_unit_factory,
    process_system_factory,
    stream_factory,
    choke_factory,
):
    """
    Does not apply downstream choking when baseline outlet pressure is already below the target.
    """
    downstream_choke = choke_factory()
    process_system = process_system_factory(
        process_units=[simple_process_unit_factory(pressure_multiplier=1), downstream_choke],
    )
    runner = DownstreamChokeRunner(process_system=process_system, downstream_choke=downstream_choke)
    strategy = DownstreamChokePressureControlStrategy(runner=runner)

    inlet_stream = stream_factory(standard_rate_m3_per_day=1000, pressure_bara=50)
    target = FloatConstraint(70.0, abs_tol=1e-12)

    success = strategy.apply(target_pressure=target, inlet_stream=inlet_stream)

    assert success is False

    # Ensure choke is not applied (baseline-run uses delta_pressure=0.0)
    outlet_stream_after_choke = runner.run(inlet_stream=inlet_stream, downstream_delta_pressure=0.0)
    assert outlet_stream_after_choke.pressure_bara == pytest.approx(50.0, abs=1e-12)


def test_downstream_choke_strategy_baseline_above_target_chokes_to_target(
    simple_process_unit_factory,
    process_system_factory,
    stream_factory,
    choke_factory,
):
    """Applies downstream choking when baseline outlet pressure is above the target, so outlet meets target."""
    downstream_choke = choke_factory()
    process_system = process_system_factory(
        process_units=[simple_process_unit_factory(pressure_multiplier=1), downstream_choke],
    )
    runner = DownstreamChokeRunner(process_system=process_system, downstream_choke=downstream_choke)
    strategy = DownstreamChokePressureControlStrategy(runner=runner)

    inlet_stream = stream_factory(standard_rate_m3_per_day=1000, pressure_bara=100)
    target = FloatConstraint(70.0, abs_tol=1e-12)

    success = strategy.apply(target_pressure=target, inlet_stream=inlet_stream)
    assert success is True

    # Confirm outlet is at target with the choke state set by the strategy.
    outlet_stream_after_choke = process_system.propagate_stream(inlet_stream=inlet_stream)
    assert outlet_stream_after_choke.pressure_bara == pytest.approx(target.value, abs=1e-12)
