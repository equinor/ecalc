import pytest

from libecalc.domain.process.process_solver.process_pipeline_runner import propagate_stream_many
from libecalc.domain.process.process_solver.solvers.downstream_choke_solver import (
    ChokeConfiguration,
    DownstreamChokeSolver,
)
from libecalc.domain.process.value_objects.fluid_stream import FluidStream


@pytest.mark.parametrize(
    "inlet_pressure, target_pressure, expected_pressure",
    [
        (100, 70, 70),  # Choked
        (50, 70, 50),  # Not choked
    ],
)
def test_downstream_choke_solver(
    simple_process_unit_factory,
    fluid_service,
    stream_factory,
    inlet_pressure,
    target_pressure,
    expected_pressure,
    choke_factory,
):
    downstream_choke = choke_factory()
    process_units = [simple_process_unit_factory(pressure_multiplier=1), downstream_choke]

    inlet_stream = stream_factory(standard_rate_m3_per_day=1000, pressure_bara=inlet_pressure)

    downstream_choke_solver = DownstreamChokeSolver(target_pressure=target_pressure)

    def choke_func(config: ChokeConfiguration) -> FluidStream:
        downstream_choke.set_pressure_change(pressure_change=config.delta_pressure)
        return propagate_stream_many(process_units=process_units, inlet_stream=inlet_stream)

    choke_solution = downstream_choke_solver.solve(func=choke_func)

    outlet_stream = choke_func(choke_solution.configuration)

    assert outlet_stream.pressure_bara == expected_pressure
