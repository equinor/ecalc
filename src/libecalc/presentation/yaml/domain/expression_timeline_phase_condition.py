from dataclasses import dataclass

from libecalc.common.variables import ExpressionEvaluator
from libecalc.ecalc_model.timeline_phase import TimelinePhaseCondition
from libecalc.expression.expression import Expression


@dataclass(frozen=True)
class ExpressionTimelinePhaseCondition(TimelinePhaseCondition):
    expression: Expression

    def get_values(self, expression_evaluator: ExpressionEvaluator) -> list[bool]:
        return expression_evaluator.evaluate_boolean(self.expression).tolist()
