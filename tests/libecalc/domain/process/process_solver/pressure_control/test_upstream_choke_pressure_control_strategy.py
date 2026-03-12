from libecalc.domain.process.process_solver.float_constraint import FloatConstraint
from libecalc.domain.process.process_solver.pressure_control.upstream_choke import (
    UpstreamChokePressureControlStrategy,
    UpstreamChokeRunner,
)


def test_upstream_choke_strategy_baseline_below_target_does_not_choke(
    simple_process_unit_factory,
    process_system_factory,
    stream_factory,
    choke_factory,
    root_finding_strategy,
):
    """
    Does not apply upstream choking when baseline outlet pressure is already below the target.
    """
    upstream_choke = choke_factory()
    process_system = process_system_factory(
        process_units=[upstream_choke, simple_process_unit_factory(pressure_multiplier=1)],
    )

    runner = UpstreamChokeRunner(process_system=process_system, upstream_choke=upstream_choke)
    strategy = UpstreamChokePressureControlStrategy(
        runner=runner,
        root_finding_strategy=root_finding_strategy,
    )

    inlet_stream = stream_factory(standard_rate_m3_per_day=1000, pressure_bara=50)
    target_pressure = FloatConstraint(70.0, abs_tol=1e-12)

    success = strategy.apply(target_pressure=target_pressure, inlet_stream=inlet_stream)
    assert success is False

    # Ensure choke is not applied (baseline-run uses delta_pressure=0.0)
    outlet_stream_no_choke = runner.run(inlet_stream=inlet_stream, upstream_delta_pressure=0.0)
    assert outlet_stream_no_choke.pressure_bara < target_pressure


def test_upstream_choke_strategy_baseline_above_target_chokes_to_target(
    simple_process_unit_factory,
    process_system_factory,
    stream_factory,
    choke_factory,
    root_finding_strategy,
):
    """Applies upstream choking when baseline outlet pressure is above the target, so outlet meets target."""
    upstream_choke = choke_factory()
    process_system = process_system_factory(
        process_units=[upstream_choke, simple_process_unit_factory(pressure_multiplier=1)],
    )

    runner = UpstreamChokeRunner(process_system=process_system, upstream_choke=upstream_choke)
    strategy = UpstreamChokePressureControlStrategy(
        runner=runner,
        root_finding_strategy=root_finding_strategy,
    )

    inlet_stream = stream_factory(standard_rate_m3_per_day=1000, pressure_bara=100)
    target_pressure = FloatConstraint(70.0, abs_tol=1e-12)

    success = strategy.apply(target_pressure=target_pressure, inlet_stream=inlet_stream)
    assert success is True

    # Confirm outlet is at target with the choke state set by the strategy.
    outlet_stream_after = process_system.propagate_stream(inlet_stream=inlet_stream)
    assert outlet_stream_after.pressure_bara == target_pressure
