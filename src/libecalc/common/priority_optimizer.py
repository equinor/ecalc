import operator
import typing
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from functools import reduce
from typing import Dict, Generic, List, TypeVar

import numpy as np
from libecalc.common.priorities import Priorities, PriorityID
from libecalc.common.units import Unit
from libecalc.common.utils.rates import (
    TimeSeriesBoolean,
    TimeSeriesString,
)

TResult = TypeVar("TResult")
TPriority = TypeVar("TPriority")


@dataclass
class PriorityOptimizerResult(Generic[TResult]):
    priorities_used: TimeSeriesString
    priority_results: Dict[datetime, Dict[PriorityID, Dict[str, TResult]]]


@dataclass
class EvaluatorResult(Generic[TResult]):
    id: str
    result: TResult
    is_valid: TimeSeriesBoolean


class PriorityOptimizer(Generic[TResult, TPriority]):
    def optimize(
        self,
        timesteps: List[datetime],
        priorities: Priorities[TPriority],
        evaluator: typing.Callable[[datetime, TPriority], List[EvaluatorResult[TResult]]],
    ) -> PriorityOptimizerResult:
        """
        Given a list of priorities, evaluate each priority using the evaluator. If the result of an evaluation is valid
        the priority is selected, if invalid try the next priority.

        We process each timestep separately.

        Args:
            timesteps: The timesteps that we want to figure out which priority to use for.
            priorities: Dict of priorities, key is used to identify the priority in the results.
            evaluator: The evaluator function gives a list of results back, each result with its own unique id.

        Returns:
            PriorityOptimizerResult: result containing priorities used and a map of the calculated results. The keys of
                the results map are the timestep used, the priority index and the id of the result.

        """
        is_valid = TimeSeriesBoolean(timesteps=timesteps, values=[False] * len(timesteps), unit=Unit.NONE)
        priorities_used = TimeSeriesString(
            timesteps=timesteps,
            values=[list(priorities.keys())[-1]] * len(timesteps),
            unit=Unit.NONE,
        )
        priority_results: Dict[datetime, Dict[PriorityID, Dict[str, TResult]]] = defaultdict(dict)

        for timestep_index, timestep in enumerate(timesteps):
            priority_results[timestep] = defaultdict(dict)
            for priority_name, priority_value in priorities.items():
                evaluator_results = evaluator(timestep, priority_value)
                for evaluator_result in evaluator_results:
                    priority_results[timestep][priority_name][evaluator_result.id] = evaluator_result.result

                # Check if consumers are valid for this operational setting, should be valid for all consumers
                all_evaluator_results_valid = reduce(
                    operator.mul, [evaluator_result.is_valid for evaluator_result in evaluator_results]
                )
                all_evaluator_results_valid_indices = np.nonzero(all_evaluator_results_valid.values)[0]
                all_evaluator_results_valid_indices_period_shifted = [
                    axis_indices + timestep_index for axis_indices in all_evaluator_results_valid_indices
                ]

                # Remove already valid indices, so we don't overwrite priority used with the latest valid
                new_valid_indices = [
                    i for i in all_evaluator_results_valid_indices_period_shifted if not is_valid.values[i]
                ]

                # Register the valid timesteps as valid and keep track of the operational setting used
                is_valid[new_valid_indices] = True
                priorities_used[new_valid_indices] = priority_name

                if all(is_valid.values):
                    # quit as soon as all time-steps are valid. This means that we do not need to test all settings.
                    break
        return PriorityOptimizerResult(
            priorities_used=priorities_used,
            priority_results=dict(priority_results),
        )
