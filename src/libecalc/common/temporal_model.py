from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Generic, Iterator, List, Literal, Optional, Tuple, TypeVar

from libecalc.common.time_utils import Period
from libecalc.dto.base import ComponentType, ConsumerUserDefinedCategoryType
from libecalc.dto.variables import VariablesMap
from libecalc.expression import Expression

ModelType = TypeVar("ModelType")


@dataclass
class Model(Generic[ModelType]):
    period: Period
    model: ModelType


class TemporalModel(Generic[ModelType]):
    id: Optional[str]
    component_type: Optional[ComponentType] = ComponentType.GENERIC
    name: Optional[str]
    user_defined_category: Optional[Dict[datetime, ConsumerUserDefinedCategoryType]]
    data: Dict[datetime, ConsumerUserDefinedCategoryType]

    def __init__(self, data: Dict[datetime, ModelType], id=None, name=None, component_type=ComponentType.GENERIC, user_defined_category=None):
        self._data = data

        self.id = id
        self.name = name
        self.component_type = component_type
        self.user_defined_category = user_defined_category

        start_times = list(data.keys())
        end_times = [*start_times[1:], datetime.max]
        self.models = [
            Model(
                period=Period(start=start_time, end=end_time),
                model=model,
            )
            for start_time, end_time, model in zip(start_times, end_times, data.values())
        ]

    def items(self) -> Iterator[Tuple[Period, ModelType]]:
        return ((model.period, model.model) for model in self.models)

    def get_model(self, timestep: datetime) -> ModelType:
        for model in self.models:
            if timestep in model.period:
                return model.model

        raise ValueError(f"Model for timestep '{timestep}' not found in Temporal model")


class TemporalExpression:
    @staticmethod
    def evaluate(
        temporal_expression: TemporalModel[Expression],
        variables_map: VariablesMap,
    ) -> List[float]:
        result = variables_map.zeros()
        for period, expression in temporal_expression.items():
            if Period.intersects(period, variables_map.period):
                start_index, end_index = period.get_timestep_indices(variables_map.time_vector)
                variables_map_for_this_period = variables_map.get_subset(start_index=start_index, end_index=end_index)
                evaluated_expression = expression.evaluate(
                    variables=variables_map_for_this_period.variables,
                    fill_length=len(variables_map_for_this_period.time_vector),
                )
                result[start_index:end_index] = evaluated_expression
        return result
