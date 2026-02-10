import pytest

from libecalc.domain.process.compressor.core.train.utils.common import EPSILON
from libecalc.domain.process.entities.process_units.choke import Choke
from libecalc.domain.process.process_solver.boundary import Boundary
from libecalc.domain.process.process_solver.solvers.upstream_choke_solver import UpstreamChokeSolver


@pytest.mark.parametrize(
    "inlet_pressure, target_pressure, expected_pressure",
    [
        (100, 70, 70),  # Choked
        (50, 70, 50),  # Not choked
    ],
)
def test_upstream_choke_solver(
    root_finding_strategy,
    simple_process_unit_factory,
    process_system_factory,
    fluid_service,
    stream_factory,
    inlet_pressure,
    target_pressure,
    expected_pressure,
):
    choke = Choke(fluid_service=fluid_service)
    process_system = process_system_factory(
        process_units=[choke, simple_process_unit_factory(pressure_multiplier=1)],
    )

    inlet_stream = stream_factory(standard_rate_m3_per_day=1000, pressure_bara=inlet_pressure)

    upstream_choke_solver = UpstreamChokeSolver(
        root_finding_strategy=root_finding_strategy,
        target_pressure=target_pressure,
        delta_pressure_boundary=Boundary(min=EPSILON, max=inlet_stream.pressure_bara - EPSILON),
        choke=choke,
    )
    assert upstream_choke_solver.solve(process_system, inlet_stream)
    outlet_stream = process_system.propagate_stream(inlet_stream=inlet_stream)

    assert outlet_stream.pressure_bara == expected_pressure
