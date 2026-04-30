import pytest

from libecalc.common.utils.ecalc_uuid import ecalc_id_generator
from libecalc.domain.process.compressor.core.train.utils.common import EPSILON
from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.process_pipeline.process_error import RateTooHighError
from libecalc.process.process_pipeline.process_unit import ProcessUnitId
from libecalc.process.process_solver.boundary import Boundary
from libecalc.process.process_solver.process_pipeline_runner import propagate_stream_many
from libecalc.process.process_solver.solvers.downstream_choke_solver import ChokeConfiguration
from libecalc.process.process_solver.solvers.upstream_choke_solver import UpstreamChokeSolver


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
    fluid_service,
    stream_factory,
    inlet_pressure,
    target_pressure,
    expected_pressure,
    choke_factory,
):
    choke = choke_factory()
    process_units = [choke, simple_process_unit_factory(pressure_multiplier=1)]

    inlet_stream = stream_factory(standard_rate_m3_per_day=1000, pressure_bara=inlet_pressure)

    upstream_choke_solver = UpstreamChokeSolver(
        root_finding_strategy=root_finding_strategy,
        target_pressure=target_pressure,
        delta_pressure_boundary=Boundary(min=EPSILON, max=inlet_stream.pressure_bara - EPSILON),
    )

    def choke_func(configuration: ChokeConfiguration) -> FluidStream:
        choke.set_pressure_change(configuration.delta_pressure)
        return propagate_stream_many(process_units=process_units, inlet_stream=inlet_stream)

    assert upstream_choke_solver.solve(choke_func)
    outlet_stream = propagate_stream_many(process_units=process_units, inlet_stream=inlet_stream)

    assert outlet_stream.pressure_bara == expected_pressure


def test_upstream_choke_solver_handles_rate_too_high_at_max_choke(
    root_finding_strategy,
    stream_factory,
):
    """
    When the upstream choke drops suction pressure so low that the downstream process unit
    raises RateTooHighError (actual volumetric rate diverges), the solver must still converge
    to the correct choke setting rather than propagating the exception.
    """
    inlet_pressure = 100.0
    # The downstream unit fails below this suction pressure (simulates a chart-limited compressor).
    feasible_suction_pressure = 20.0
    pressure_added = 50.0

    # Baseline outlet = 100 + 50 = 150. Target below that requires choking.
    # Required delta_p = inlet - (target - pressure_added) = 100 - (80 - 50) = 70.
    target_pressure = 80.0

    upstream_choke_solver = UpstreamChokeSolver(
        root_finding_strategy=root_finding_strategy,
        target_pressure=target_pressure,
        delta_pressure_boundary=Boundary(min=EPSILON, max=inlet_pressure - EPSILON),
    )

    def choke_func(configuration: ChokeConfiguration) -> FluidStream:
        suction_pressure = inlet_pressure - configuration.delta_pressure
        if suction_pressure < feasible_suction_pressure:
            # TODO: Should get ID from owning choke?
            raise RateTooHighError(process_unit_id=ProcessUnitId(ecalc_id_generator()))
        return stream_factory(
            standard_rate_m3_per_day=1000,
            pressure_bara=suction_pressure + pressure_added,
        )

    solution = upstream_choke_solver.solve(choke_func)

    assert solution.success
    assert abs(solution.configuration.delta_pressure - 70.0) < 1e-3
