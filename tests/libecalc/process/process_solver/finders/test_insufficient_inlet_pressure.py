"""Regression: InsufficientInletPressureError must not crash finders."""

from libecalc.process.process_pipeline.process_error import InsufficientInletPressureError
from libecalc.process.process_pipeline.process_unit import ProcessUnit
from libecalc.process.process_solver.boundary import Boundary
from libecalc.process.process_solver.finders.shaft_speed_finder import ShaftSpeedFinder, SpeedConfiguration
from libecalc.process.process_solver.solver import InsufficientInletPressureFailure

DROPPER_ID = ProcessUnit._create_id()


def test_shaft_speed_finder_catches_insufficient_inlet_pressure(
    search_strategy_factory,
    root_finding_strategy,
):
    """ShaftSpeedFinder returns a failure when func raises InsufficientInletPressureError."""

    def func(_config: SpeedConfiguration):
        raise InsufficientInletPressureError(
            process_unit_id=DROPPER_ID,
            inlet_pressure_bara=25.0,
            required_delta_pressure_bara=75.0,
        )

    finder = ShaftSpeedFinder(
        search_strategy=search_strategy_factory(tolerance=1.0),
        root_finding_strategy=root_finding_strategy,
        boundary=Boundary(min=50, max=100),
        target_pressure=40.0,
    )

    finding = finder.find(func)

    assert finding.failure is not None
    assert isinstance(finding.failure, InsufficientInletPressureFailure)
    assert finding.failure.process_unit_id == DROPPER_ID
