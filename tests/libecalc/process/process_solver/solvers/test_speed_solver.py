import pytest

from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.process_pipeline.process_error import (
    CompressorOperatingPoint,
    OutletFluidNotAchievableError,
    RateTooHighError,
    RateTooLowError,
)
from libecalc.process.process_pipeline.process_unit import ProcessUnit, ProcessUnitId
from libecalc.process.process_solver.boundary import Boundary
from libecalc.process.process_solver.solver import (
    OutletFluidNotAchievableFailure,
    RateTooHighFailure,
    RateTooLowFailure,
    TargetPressureUnreachableFailure,
)
from libecalc.process.process_solver.solvers.speed_solver import SpeedConfiguration, SpeedSolver


@pytest.mark.parametrize(
    "target_pressure, speed_boundary, inlet_pressure, expected_speed, expected_pressure, solution_found",
    [
        (300, Boundary(min=200, max=600), 100, 200, 300, True),  # Solution found
        (1000, Boundary(min=200, max=600), 100, 600, 700, False),  # Solution not found, max speed
        (50, Boundary(min=200, max=600), 25, 200, 225, False),  # Solution not found, min speed
    ],
)
def test_speed_solver(
    search_strategy_factory,
    root_finding_strategy,
    stream_factory,
    fluid_service,
    target_pressure,
    speed_boundary,
    inlet_pressure,
    expected_speed,
    expected_pressure,
    solution_found,
):
    speed_solver = SpeedSolver(
        search_strategy=search_strategy_factory(),
        root_finding_strategy=root_finding_strategy,
        boundary=speed_boundary,
        target_pressure=target_pressure,
    )
    inlet_stream = stream_factory(
        standard_rate_m3_per_day=1000,
        pressure_bara=inlet_pressure,
    )

    def speed_func(configuration: SpeedConfiguration) -> FluidStream:
        return fluid_service.create_stream_from_standard_rate(
            fluid_model=inlet_stream.fluid_model,
            pressure_bara=inlet_stream.pressure_bara + configuration.speed,
            standard_rate_m3_per_day=inlet_stream.standard_rate_sm3_per_day,
            temperature_kelvin=inlet_stream.temperature_kelvin,
        )

    solution = speed_solver.solve(speed_func)

    assert solution.success == solution_found

    assert solution.configuration.speed == expected_speed
    outlet_stream = speed_func(solution.configuration)
    assert outlet_stream.pressure_bara == expected_pressure


def test_max_speed_rate_too_high_returns_capacity_failure(
    search_strategy_factory,
    root_finding_strategy,
):
    process_unit_id = ProcessUnit._create_id()
    actual_rate = 2000.0
    boundary_rate = 1000.0
    speed_solver = SpeedSolver(
        search_strategy=search_strategy_factory(),
        root_finding_strategy=root_finding_strategy,
        boundary=Boundary(min=200, max=600),
        target_pressure=450,
    )

    def speed_func(configuration: SpeedConfiguration):
        raise RateTooHighError(
            process_unit_id=process_unit_id,
            actual_rate=actual_rate,
            boundary_rate=boundary_rate,
        )

    solution = speed_solver.solve(speed_func)

    assert solution.success is False
    assert solution.configuration.speed == 600
    assert isinstance(solution.failure, RateTooHighFailure)
    assert solution.failure.actual_rate_m3_per_hour == actual_rate
    assert solution.failure.maximum_rate_m3_per_hour == boundary_rate
    assert solution.failure.source_id == process_unit_id


def test_max_speed_rate_too_low_returns_capacity_failure(
    search_strategy_factory,
    root_finding_strategy,
):
    process_unit_id = ProcessUnit._create_id()
    actual_rate = 50.0
    boundary_rate = 100.0
    speed_solver = SpeedSolver(
        search_strategy=search_strategy_factory(),
        root_finding_strategy=root_finding_strategy,
        boundary=Boundary(min=200, max=600),
        target_pressure=450,
    )

    def speed_func(configuration: SpeedConfiguration):
        raise RateTooLowError(
            process_unit_id=process_unit_id,
            actual_rate=actual_rate,
            boundary_rate=boundary_rate,
        )

    solution = speed_solver.solve(speed_func)

    assert solution.success is False
    assert solution.configuration.speed == 600
    assert isinstance(solution.failure, RateTooLowFailure)
    assert solution.failure.actual_rate_m3_per_hour == actual_rate
    assert solution.failure.minimum_rate_m3_per_hour == boundary_rate
    assert solution.failure.source_id == process_unit_id


def _outlet_fluid_not_achievable_error(
    process_unit_id: ProcessUnitId,
    inlet_stream: FluidStream,
    speed: float,
) -> OutletFluidNotAchievableError:
    return OutletFluidNotAchievableError(
        process_unit_id=process_unit_id,
        unachievable_operating_point=CompressorOperatingPoint(
            inlet_pressure_bara=inlet_stream.pressure_bara,
            inlet_temperature_kelvin=inlet_stream.temperature_kelvin,
            actual_rate_m3_per_hour=0.0,
            polytropic_head_joule_per_kg=0.0,
            polytropic_efficiency=0.0,
            speed=speed,
        ),
    )


def test_min_speed_outlet_fluid_not_achievable_target_achievable(
    search_strategy_factory,
    root_finding_strategy,
    stream_factory,
    fluid_service,
):
    process_unit_id = ProcessUnit._create_id()
    speed_solver = SpeedSolver(
        search_strategy=search_strategy_factory(),
        root_finding_strategy=root_finding_strategy,
        boundary=Boundary(min=200, max=600),
        target_pressure=450,
    )
    inlet_stream = stream_factory(standard_rate_m3_per_day=1000, pressure_bara=100)

    def speed_func(configuration: SpeedConfiguration) -> FluidStream:
        if configuration.speed <= 300:
            raise _outlet_fluid_not_achievable_error(process_unit_id, inlet_stream, configuration.speed)
        return fluid_service.create_stream_from_standard_rate(
            fluid_model=inlet_stream.fluid_model,
            pressure_bara=inlet_stream.pressure_bara + configuration.speed,
            standard_rate_m3_per_day=inlet_stream.standard_rate_sm3_per_day,
            temperature_kelvin=inlet_stream.temperature_kelvin,
        )

    solution = speed_solver.solve(speed_func)

    assert solution.success is True
    assert solution.configuration.speed == pytest.approx(350)


def test_max_speed_outlet_fluid_not_achievable_target_achievable(
    search_strategy_factory,
    root_finding_strategy,
    stream_factory,
    fluid_service,
):
    process_unit_id = ProcessUnit._create_id()
    speed_solver = SpeedSolver(
        search_strategy=search_strategy_factory(),
        root_finding_strategy=root_finding_strategy,
        boundary=Boundary(min=200, max=600),
        target_pressure=350,
    )
    inlet_stream = stream_factory(standard_rate_m3_per_day=1000, pressure_bara=100)

    def speed_func(configuration: SpeedConfiguration) -> FluidStream:
        if configuration.speed >= 500:
            raise _outlet_fluid_not_achievable_error(process_unit_id, inlet_stream, configuration.speed)
        return fluid_service.create_stream_from_standard_rate(
            fluid_model=inlet_stream.fluid_model,
            pressure_bara=inlet_stream.pressure_bara + configuration.speed,
            standard_rate_m3_per_day=inlet_stream.standard_rate_sm3_per_day,
            temperature_kelvin=inlet_stream.temperature_kelvin,
        )

    solution = speed_solver.solve(speed_func)

    assert solution.success is True
    assert solution.configuration.speed == pytest.approx(250)


def test_max_speed_outlet_fluid_not_achievable_target_not_achievable(
    search_strategy_factory,
    root_finding_strategy,
    stream_factory,
    fluid_service,
):
    process_unit_id = ProcessUnit._create_id()
    speed_solver = SpeedSolver(
        search_strategy=search_strategy_factory(),
        root_finding_strategy=root_finding_strategy,
        boundary=Boundary(min=200, max=600),
        target_pressure=500,
    )
    inlet_stream = stream_factory(standard_rate_m3_per_day=1000, pressure_bara=100)

    def speed_func(configuration: SpeedConfiguration) -> FluidStream:
        if configuration.speed >= 300:
            raise _outlet_fluid_not_achievable_error(process_unit_id, inlet_stream, configuration.speed)
        return fluid_service.create_stream_from_standard_rate(
            fluid_model=inlet_stream.fluid_model,
            pressure_bara=inlet_stream.pressure_bara + configuration.speed,
            standard_rate_m3_per_day=inlet_stream.standard_rate_sm3_per_day,
            temperature_kelvin=inlet_stream.temperature_kelvin,
        )

    solution = speed_solver.solve(speed_func)

    assert solution.success is False
    assert isinstance(solution.failure, TargetPressureUnreachableFailure)
    assert solution.failure.achievable_pressure_bara < 500
    assert solution.failure.target_pressure_bara == 500
    assert solution.configuration.speed < 600
    assert solution.configuration.speed == pytest.approx(300, abs=1.0)


def test_capacity_at_low_speed_and_outlet_fluid_not_achievable_at_high_speed(
    search_strategy_factory,
    root_finding_strategy,
    stream_factory,
    fluid_service,
):
    process_unit_id = ProcessUnit._create_id()
    speed_solver = SpeedSolver(
        search_strategy=search_strategy_factory(),
        root_finding_strategy=root_finding_strategy,
        boundary=Boundary(min=200, max=600),
        target_pressure=450,
    )
    inlet_stream = stream_factory(standard_rate_m3_per_day=1000, pressure_bara=100)

    def speed_func(configuration: SpeedConfiguration) -> FluidStream:
        if configuration.speed < 300:
            raise RateTooHighError(actual_rate=2000.0, boundary_rate=1000.0, process_unit_id=process_unit_id)
        if configuration.speed > 500:
            raise _outlet_fluid_not_achievable_error(process_unit_id, inlet_stream, configuration.speed)
        return fluid_service.create_stream_from_standard_rate(
            fluid_model=inlet_stream.fluid_model,
            pressure_bara=inlet_stream.pressure_bara + configuration.speed,
            standard_rate_m3_per_day=inlet_stream.standard_rate_sm3_per_day,
            temperature_kelvin=inlet_stream.temperature_kelvin,
        )

    solution = speed_solver.solve(speed_func)

    assert solution.success is True
    assert 300 <= solution.configuration.speed <= 500
    assert solution.configuration.speed == pytest.approx(350)


def test_all_speeds_outlet_fluid_not_achievable_returns_failure(
    search_strategy_factory,
    root_finding_strategy,
    stream_factory,
):
    process_unit_id = ProcessUnit._create_id()
    speed_solver = SpeedSolver(
        search_strategy=search_strategy_factory(),
        root_finding_strategy=root_finding_strategy,
        boundary=Boundary(min=200, max=600),
        target_pressure=350,
    )
    inlet_stream = stream_factory(standard_rate_m3_per_day=1000, pressure_bara=100)

    def speed_func(configuration: SpeedConfiguration) -> FluidStream:
        raise _outlet_fluid_not_achievable_error(process_unit_id, inlet_stream, configuration.speed)

    solution = speed_solver.solve(speed_func)

    assert solution.success is False
    assert isinstance(solution.failure, OutletFluidNotAchievableFailure)
