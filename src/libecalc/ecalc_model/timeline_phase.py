from abc import ABC, abstractmethod
from enum import StrEnum

from libecalc.common.ddd import value_object
from libecalc.common.errors.ecalc_validation_error import EcalcValidationException
from libecalc.common.variables import ExpressionCannotEvaluateToBooleanValueException, ExpressionEvaluator


class TimelinePhaseType(StrEnum):
    DRILLING = "DRILLING"
    PRODUCTION = "PRODUCTION"
    OFFLOADING = "OFFLOADING"
    TURNOVER = "TURNOVER"


class TimelinePhaseCondition(ABC):
    @abstractmethod
    def get_values(self, expression_evaluator: ExpressionEvaluator) -> list[bool]:
        """Whether the condition is true in each period of the expression evaluator."""


@value_object
class TimelinePhase:
    reference: str
    title: str
    type: TimelinePhaseType
    when: TimelinePhaseCondition
    description: str | None


class TimelinePhaseNotFoundException(EcalcValidationException):
    def __init__(self, reference: str):
        super().__init__(f"Phase reference '{reference}' does not match any phase in TIMELINE.PHASES.")


class TimelinePhaseCannotEvaluateToBooleanValueException(EcalcValidationException):
    def __init__(self, reference: str, invalid_values: list[float]):
        values = ", ".join(f"{value:g}" for value in invalid_values)
        super().__init__(
            f"WHEN of phase '{reference}' must evaluate to true or false (1 or 0) in every period, got {values}."
        )


class TimelinePhaseService:
    def __init__(self, timeline_phases: list[TimelinePhase]):
        self._timeline_phases = {timeline_phase.reference: timeline_phase for timeline_phase in timeline_phases}

    def get_phase_by_reference(self, reference: str) -> TimelinePhase:
        if reference not in self._timeline_phases:
            raise TimelinePhaseNotFoundException(reference)
        return self._timeline_phases[reference]

    def is_active(self, reference: str, expression_evaluator: ExpressionEvaluator) -> list[bool]:
        """Whether the phase is active in each period of the expression evaluator."""
        phase = self.get_phase_by_reference(reference)
        try:
            return phase.when.get_values(expression_evaluator)
        except ExpressionCannotEvaluateToBooleanValueException as e:
            raise TimelinePhaseCannotEvaluateToBooleanValueException(reference, e.invalid_values) from e
