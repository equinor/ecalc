import operator
import typing
from collections import defaultdict
from dataclasses import dataclass
from functools import reduce
from typing import Dict, Generic, List, TypeVar

from libecalc.common.priorities import PriorityID

ComponentID = str


class EvaluatorResult(typing.Protocol):
    id: ComponentID
    is_valid: bool


TResult = TypeVar("TResult", bound=EvaluatorResult)


@dataclass
class PriorityOptimizerResult(Generic[TResult]):
    priority_used: PriorityID
    priority_results: List[TResult]


class PriorityOptimizer:
    def optimize(
        self,
        priorities: List[PriorityID],
        evaluator: typing.Callable[[PriorityID], List[TResult]],
    ) -> PriorityOptimizerResult[TResult]:
        """
        Given a list of priorities, evaluate each priority using the evaluator. If the result of an evaluation is valid
        the priority is selected, if invalid try the next priority.

        It will default to the last priority if all settings fails

        Args:
            priorities: List of priorities
            evaluator: The evaluator function gives a list of results back, each result with its own unique id.

        Returns:
            PriorityOptimizerResult: result containing priorities used and a list of the results merged on priorities
            used,

        """
        priority_used = priorities[-1]
        priority_results: Dict[PriorityID, Dict[str, TResult]] = defaultdict(dict)

        for priority in priorities:
            evaluator_results = evaluator(priority)
            for evaluator_result in evaluator_results:
                priority_results[priority][evaluator_result.id] = evaluator_result

            # Check if consumers are valid for this priority, should be valid for all consumers
            all_evaluator_results_valid = reduce(
                operator.mul, [evaluator_result.is_valid for evaluator_result in evaluator_results]
            )

            if all_evaluator_results_valid:
                priority_used = priority
                # quit as soon as all time-steps are valid. This means that we do not need to test all settings.
                break
        return PriorityOptimizerResult(
            priority_used=priority_used,
            priority_results=list(priority_results[priority_used].values()),
        )
