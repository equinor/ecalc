from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from datetime import datetime
from typing import Generic, TypeVar

from libecalc.common.time_utils import Period

ModelType = TypeVar("ModelType")


@dataclass
class Model(Generic[ModelType]):
    period: Period
    model: ModelType


class TemporalModel(Generic[ModelType]):
    """If data has datetime keys, convert to Period keys"""

    def __init__(self, data: dict[datetime, ModelType] | dict[Period, ModelType]):
        if all(isinstance(key, datetime) for key in data.keys()):
            # convert date keys to Period keys
            model_dates = list(data.keys()) + [datetime.max.replace(microsecond=0)]
            data = {
                Period(start=start_time, end=end_time): model
                for start_time, end_time, model in zip(model_dates[:-1], model_dates[1:], data.values())
            }
        self._data = data
        self.models = [
            Model(
                period=period,
                model=model,
            )
            for period, model in data.items()
        ]

    def get_periods(self) -> Iterable[Period]:
        return [model.period for model in self.models]

    def items(self) -> Iterator[tuple[Period, ModelType]]:
        return ((model.period, model.model) for model in self.models)

    def get_model(self, period: Period) -> ModelType:
        for model in self.models:
            if period in model.period:
                return model.model

        raise ValueError(f"Model for timestep '{period}' not found in Temporal model")
