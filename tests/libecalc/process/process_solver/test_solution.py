from libecalc.process.process_pipeline.process_unit import ProcessUnitId
from libecalc.process.process_solver.configuration import (
    Configuration,
    ConfigurationHandlerId,
    SpeedConfiguration,
)
from libecalc.process.process_solver.solver import (
    RateTooHighFailure,
    RateTooLowFailure,
    Solution,
)


def _shaft_config(speed: float) -> Configuration[SpeedConfiguration]:
    return Configuration(
        configuration_handler_id=ConfigurationHandlerId("shaft"),
        value=SpeedConfiguration(speed=speed),
    )


def test_combine_propagates_others_failure_when_self_succeeded():
    failure = RateTooHighFailure(source_id=ProcessUnitId("u1"))
    success_solution: Solution = Solution(configuration=[])
    failing_solution: Solution = Solution(configuration=[], failure=failure)

    combined = success_solution.combine(failing_solution)

    assert combined.success is False
    assert combined.failure is failure


def test_combine_short_circuits_when_self_already_failed():
    """Once a stage fails, the failure must keep referring to the configurations it was generated from."""
    self_failure = RateTooLowFailure(source_id=ProcessUnitId("u1"))
    failed = Solution(configuration=[_shaft_config(100.0)], failure=self_failure)
    later = Solution(configuration=[_shaft_config(200.0)])

    combined = failed.combine(later)

    assert combined is failed
    assert combined.failure is self_failure
    assert combined.configuration == [_shaft_config(100.0)]


def test_combine_short_circuits_even_when_other_also_failed():
    self_failure = RateTooLowFailure(source_id=ProcessUnitId("u1"))
    other_failure = RateTooHighFailure(source_id=ProcessUnitId("u2"))
    a: Solution = Solution(configuration=[], failure=self_failure)
    b: Solution = Solution(configuration=[], failure=other_failure)

    combined = a.combine(b)

    assert combined.failure is self_failure
