from libecalc.domain.process.process_solver.float_constraint import FloatConstraint
from libecalc.domain.process.process_solver.pressure_control.upstream_choke import (
    UpstreamChokePressureControlStrategy,
)


def test_upstream_choke_strategy_baseline_below_target_does_not_choke(
    simple_process_unit_factory,
    stream_factory,
    choke_factory,
    choke_configuration_handler_factory,
    root_finding_strategy,
    process_runner_factory,
):
    """
    Does not apply upstream choking when baseline outlet pressure is already below the target.
    """
    upstream_choke = choke_factory()
    upstream_choke_configuration_handler = choke_configuration_handler_factory(choke=upstream_choke)
    process_units = [upstream_choke, simple_process_unit_factory(pressure_multiplier=1)]

    runner = process_runner_factory(units=process_units, configuration_handlers=[upstream_choke_configuration_handler])
    strategy = UpstreamChokePressureControlStrategy(
        simulator=runner,
        choke_configuration_handler_id=upstream_choke_configuration_handler.get_id(),
        root_finding_strategy=root_finding_strategy,
    )

    inlet_stream = stream_factory(standard_rate_m3_per_day=1000, pressure_bara=50)
    target_pressure = FloatConstraint(70.0, abs_tol=1e-12)

    solution = strategy.apply(target_pressure=target_pressure, inlet_stream=inlet_stream)
    assert solution.success is False

    choke_configuration = [
        config
        for config in solution.configuration
        if config.configuration_handler_id == upstream_choke_configuration_handler.get_id()
    ][0]
    assert choke_configuration.value.delta_pressure == 0

    # Ensure choke is not applied (baseline-run uses delta_pressure=0.0)
    runner.apply_configurations(solution.configuration)
    outlet_stream_no_choke = runner.run(inlet_stream=inlet_stream)
    assert outlet_stream_no_choke.pressure_bara < target_pressure


def test_upstream_choke_strategy_baseline_above_target_chokes_to_target(
    simple_process_unit_factory,
    stream_factory,
    choke_factory,
    choke_configuration_handler_factory,
    root_finding_strategy,
    process_runner_factory,
):
    """Applies upstream choking when baseline outlet pressure is above the target, so outlet meets target."""
    upstream_choke = choke_factory()
    upstream_choke_configuration_handler = choke_configuration_handler_factory(choke=upstream_choke)
    process_units = [upstream_choke, simple_process_unit_factory(pressure_multiplier=1)]

    runner = process_runner_factory(units=process_units, configuration_handlers=[upstream_choke_configuration_handler])
    strategy = UpstreamChokePressureControlStrategy(
        simulator=runner,
        choke_configuration_handler_id=upstream_choke_configuration_handler.get_id(),
        root_finding_strategy=root_finding_strategy,
    )

    inlet_stream = stream_factory(standard_rate_m3_per_day=1000, pressure_bara=100)
    target_pressure = FloatConstraint(70.0, abs_tol=1e-12)

    solution = strategy.apply(target_pressure=target_pressure, inlet_stream=inlet_stream)
    assert solution.success is True

    choke_configuration = [
        config
        for config in solution.configuration
        if config.configuration_handler_id == upstream_choke_configuration_handler.get_id()
    ][0]
    assert choke_configuration.value.delta_pressure > 0

    # Confirm outlet is at target with the choke state set by the strategy.
    runner.apply_configurations(solution.configuration)
    outlet_stream_after = runner.run(inlet_stream=inlet_stream)
    assert outlet_stream_after.pressure_bara == target_pressure
