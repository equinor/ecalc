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
            model_dates: list[datetime] = list(data.keys()) + [datetime.max.replace(microsecond=0)]
            for start_time, end_time in zip(model_dates[:-1], model_dates[1:]):
                if not (isinstance(start_time, datetime) and isinstance(end_time, datetime)):
                    raise TypeError("All keys must be datetime when converting to Period.")
            data = {
                Period(start=start_time, end=end_time): model
                for start_time, end_time, model in zip(model_dates[:-1], model_dates[1:], data.values())
            }
        elif not all(isinstance(key, Period) for key in data.keys()):
            raise TypeError("All keys must be either datetime or Period.")
        self._data = data
        self.models = []
        for period, model in data.items():
            if not isinstance(period, Period):
                raise TypeError(f"Expected Period, got {type(period)}")
            self.models.append(Model(period=period, model=model))

    def get_periods(self) -> Iterable[Period]:
        return [model.period for model in self.models]

    def items(self) -> Iterator[tuple[Period, ModelType]]:
        return ((model.period, model.model) for model in self.models)

    def get_model(self, period: Period | datetime) -> ModelType:
        for model in self.models:
            if period in model.period:
                return model.model

        raise ValueError(f"Model for timestep '{period}' not found in Temporal model")
