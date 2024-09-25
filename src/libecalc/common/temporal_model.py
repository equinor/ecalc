from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Generic, Iterator, Tuple, TypeVar

from libecalc.common.time_utils import Period

ModelType = TypeVar("ModelType")


@dataclass
class Model(Generic[ModelType]):
    period: Period
    model: ModelType


class TemporalModel(Generic[ModelType]):
    def __init__(self, data: Dict[datetime, ModelType]):
        self._data = data
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
