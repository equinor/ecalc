from libecalc.domain.process.process_solver.float_constraint import FloatConstraint
from libecalc.domain.process.process_solver.pressure_control.downstream_choke import (
    DownstreamChokePressureControlStrategy,
)


def test_downstream_choke_strategy_baseline_below_target_does_not_choke(
    simple_process_unit_factory,
    stream_factory,
    choke_factory,
    choke_configuration_handler_factory,
    process_runner_factory,
):
    """
    Does not apply downstream choking when baseline outlet pressure is already below the target.
    """
    downstream_choke = choke_factory()
    downstream_choke_configuration_handler = choke_configuration_handler_factory(choke=downstream_choke)
    process_units = [simple_process_unit_factory(pressure_multiplier=1), downstream_choke]
    runner = process_runner_factory(
        units=process_units, configuration_handlers=[downstream_choke_configuration_handler]
    )
    strategy = DownstreamChokePressureControlStrategy(
        simulator=runner, choke_configuration_handler_id=downstream_choke_configuration_handler.get_id()
    )

    inlet_stream = stream_factory(standard_rate_m3_per_day=1000, pressure_bara=50)
    target = FloatConstraint(70.0, abs_tol=1e-12)

    solution = strategy.apply(target_pressure=target, inlet_stream=inlet_stream)

    assert solution.success is False

    choke_configuration = [
        config
        for config in solution.configuration
        if config.configuration_handler_id == downstream_choke_configuration_handler.get_id()
    ][0]
    assert choke_configuration.value.delta_pressure == 0

    runner.apply_configurations(solution.configuration)
    assert runner.run(inlet_stream=inlet_stream).pressure_bara < target


def test_downstream_choke_strategy_baseline_above_target_chokes_to_target(
    simple_process_unit_factory,
    stream_factory,
    choke_factory,
    choke_configuration_handler_factory,
    process_runner_factory,
):
    """Applies downstream choking when baseline outlet pressure is above the target, so outlet meets target."""
    downstream_choke = choke_factory()
    downstream_choke_configuration_handler = choke_configuration_handler_factory(choke=downstream_choke)
    process_units = [simple_process_unit_factory(pressure_multiplier=1), downstream_choke]
    runner = process_runner_factory(
        units=process_units, configuration_handlers=[downstream_choke_configuration_handler]
    )
    strategy = DownstreamChokePressureControlStrategy(
        simulator=runner, choke_configuration_handler_id=downstream_choke_configuration_handler.get_id()
    )

    inlet_stream = stream_factory(standard_rate_m3_per_day=1000, pressure_bara=100)
    target = FloatConstraint(70.0, abs_tol=1e-12)

    solution = strategy.apply(target_pressure=target, inlet_stream=inlet_stream)
    assert solution.success is True

    choke_configuration = [
        config
        for config in solution.configuration
        if config.configuration_handler_id == downstream_choke_configuration_handler.get_id()
    ][0]
    assert choke_configuration.value.delta_pressure > 0

    # Confirm outlet is at target with the choke state set by the strategy.
    runner.apply_configurations(solution.configuration)
    assert runner.run(inlet_stream=inlet_stream).pressure_bara == target
