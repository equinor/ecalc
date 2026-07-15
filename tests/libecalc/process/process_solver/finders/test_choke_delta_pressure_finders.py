from libecalc.common.utils.ecalc_uuid import ecalc_id_generator
from libecalc.domain.process.compressor.core.train.utils.common import EPSILON
from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.process_pipeline.process_error import CompressorStonewallError
from libecalc.process.process_pipeline.process_unit import ProcessUnitId
from libecalc.process.process_solver.boundary import Boundary
from libecalc.process.process_solver.finders.choke_delta_pressure_finders import (
    ChokeConfiguration,
    DownstreamChokeDeltaPressureFinder,
    UpstreamChokeDeltaPressureFinder,
)
from libecalc.process.process_solver.process_pipeline_runner import propagate_stream_many
from libecalc.process.process_solver.solver import CompressorStonewallFailure


def test_upstream_choke_solver(
    root_finding_strategy,
    simple_process_unit_factory,
    fluid_service,
    stream_factory,
    choke_factory,
):
    choke = choke_factory()
    process_units = [choke, simple_process_unit_factory(pressure_multiplier=1)]

    inlet_stream = stream_factory(standard_rate_m3_per_day=1000, pressure_bara=100)

    upstream_choke_search = UpstreamChokeDeltaPressureFinder(
        root_finding_strategy=root_finding_strategy,
        target_pressure=70,
        delta_pressure_boundary=Boundary(min=EPSILON, max=inlet_stream.pressure_bara - EPSILON),
    )

    def choke_func(configuration: ChokeConfiguration) -> FluidStream:
        choke.set_pressure_change(configuration.delta_pressure)
        return propagate_stream_many(process_units=process_units, inlet_stream=inlet_stream)

    upstream_choke_search.find(choke_func)
    outlet_stream = propagate_stream_many(process_units=process_units, inlet_stream=inlet_stream)

    assert outlet_stream.pressure_bara == 70


def test_upstream_choke_solver_handles_rate_too_high_at_max_choke(
    root_finding_strategy,
    stream_factory,
):
    """
    When the upstream choke drops suction pressure so low that the downstream process unit
    raises CompressorStonewallError, the solver must still converge to the correct choke setting.
    """
    inlet_pressure = 100.0
    feasible_suction_pressure = 20.0
    pressure_added = 50.0
    target_pressure = 80.0  # Requires dp=70; feasible (suction=30 > 20).

    upstream_choke_search = UpstreamChokeDeltaPressureFinder(
        root_finding_strategy=root_finding_strategy,
        target_pressure=target_pressure,
        delta_pressure_boundary=Boundary(min=EPSILON, max=inlet_pressure - EPSILON),
    )

    def choke_func(configuration: ChokeConfiguration) -> FluidStream:
        suction_pressure = inlet_pressure - configuration.delta_pressure
        if suction_pressure < feasible_suction_pressure:
            raise CompressorStonewallError(process_unit_id=ProcessUnitId(ecalc_id_generator()))
        return stream_factory(
            standard_rate_m3_per_day=1000,
            pressure_bara=suction_pressure + pressure_added,
        )

    result = upstream_choke_search.find(choke_func)

    assert abs(result.configuration.delta_pressure - 70.0) < 1e-3


def test_upstream_choke_solver_reports_rate_too_high_when_stonewall_prevents_reaching_target(
    root_finding_strategy,
    stream_factory,
):
    """When choking further would raise CompressorStonewallError AND the maximum feasible choke
    still leaves outlet pressure above target, the failure must be CompressorStonewallFailure.
    """
    inlet_pressure = 100.0
    feasible_suction_minimum = 60.0
    pressure_added = 50.0
    target_pressure = 80.0  # Requires dp=70, infeasible (max feasible dp=40)

    upstream_choke_search = UpstreamChokeDeltaPressureFinder(
        root_finding_strategy=root_finding_strategy,
        target_pressure=target_pressure,
        delta_pressure_boundary=Boundary(min=EPSILON, max=inlet_pressure - EPSILON),
    )

    def choke_func(configuration: ChokeConfiguration) -> FluidStream:
        suction_pressure = inlet_pressure - configuration.delta_pressure
        if suction_pressure < feasible_suction_minimum:
            raise CompressorStonewallError(process_unit_id=ProcessUnitId(ecalc_id_generator()))
        return stream_factory(
            standard_rate_m3_per_day=1000,
            pressure_bara=suction_pressure + pressure_added,
        )

    result = upstream_choke_search.find(choke_func)

    assert not result.success
    assert isinstance(result.failure, CompressorStonewallFailure)


def test_upstream_choke_solver_reports_failure_when_max_choke_still_above_target(
    root_finding_strategy,
    stream_factory,
):
    inlet_pressure = 100.0
    pressure_added = 200.0
    target_pressure = 80.0

    upstream_choke_search = UpstreamChokeDeltaPressureFinder(
        root_finding_strategy=root_finding_strategy,
        target_pressure=target_pressure,
        delta_pressure_boundary=Boundary(min=EPSILON, max=inlet_pressure - EPSILON),
    )

    def choke_func(configuration: ChokeConfiguration) -> FluidStream:
        suction_pressure = inlet_pressure - configuration.delta_pressure
        return stream_factory(
            standard_rate_m3_per_day=1000,
            pressure_bara=suction_pressure + pressure_added,
        )

    result = upstream_choke_search.find(choke_func)

    assert not result.success
    failure = result.failure
    assert failure.target_pressure_bara == target_pressure
    assert failure.achievable_pressure_bara > target_pressure


def test_downstream_choke_solver(
    simple_process_unit_factory,
    fluid_service,
    stream_factory,
    choke_factory,
):
    """Outlet above target: choke is applied to reach target pressure."""
    downstream_choke = choke_factory()
    process_units = [simple_process_unit_factory(pressure_multiplier=1), downstream_choke]

    inlet_stream = stream_factory(standard_rate_m3_per_day=1000, pressure_bara=100)
    target_pressure = 70

    downstream_choke_search = DownstreamChokeDeltaPressureFinder(target_pressure=target_pressure)

    def choke_func(config: ChokeConfiguration) -> FluidStream:
        downstream_choke.set_pressure_change(pressure_change=config.delta_pressure)
        return propagate_stream_many(process_units=process_units, inlet_stream=inlet_stream)

    result = downstream_choke_search.find(func=choke_func)

    outlet_stream = choke_func(result.configuration)
    assert outlet_stream.pressure_bara == target_pressure


def test_downstream_choke_solver_fails_when_outlet_below_target(
    simple_process_unit_factory,
    stream_factory,
    choke_factory,
):
    """Outlet already below target: finder returns failure."""
    downstream_choke = choke_factory()
    process_units = [simple_process_unit_factory(pressure_multiplier=1), downstream_choke]

    inlet_stream = stream_factory(standard_rate_m3_per_day=1000, pressure_bara=50)
    target_pressure = 70

    downstream_choke_search = DownstreamChokeDeltaPressureFinder(target_pressure=target_pressure)

    def choke_func(config: ChokeConfiguration) -> FluidStream:
        downstream_choke.set_pressure_change(pressure_change=config.delta_pressure)
        return propagate_stream_many(process_units=process_units, inlet_stream=inlet_stream)

    result = downstream_choke_search.find(func=choke_func)
    assert not result.success
