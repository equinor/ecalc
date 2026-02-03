import pytest

from libecalc.domain.process.entities.choke import Choke
from libecalc.domain.process.process_solver.solvers.downstream_choke_solver import DownstreamChokeSolver


@pytest.mark.parametrize(
    "inlet_pressure, target_pressure, expected_pressure",
    [
        (100, 70, 70),  # Choked
        (50, 70, 50),  # Not choked
    ],
)
def test_downstream_choke_solver(
    simple_process_unit_factory,
    process_system_factory,
    fluid_service,
    stream_factory,
    inlet_pressure,
    target_pressure,
    expected_pressure,
):
    downstream_choke = Choke(fluid_service=fluid_service)
    process_system = process_system_factory(
        downstream_choke=downstream_choke,
        process_units=[simple_process_unit_factory(pressure_multiplier=1)],
    )

    inlet_stream = stream_factory(standard_rate_m3_per_day=1000, pressure_bara=inlet_pressure)

    downstream_choke_solver = DownstreamChokeSolver(target_pressure=target_pressure)
    outlet_stream = downstream_choke_solver.solve(process_system, inlet_stream)

    assert outlet_stream.pressure_bara == expected_pressure
