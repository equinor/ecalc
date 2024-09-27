from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Generic, Iterable, Iterator, Tuple, TypeVar

from libecalc.common.time_utils import Period

ModelType = TypeVar("ModelType")


@dataclass
class Model(Generic[ModelType]):
    period: Period
    model: ModelType


class TemporalModel(Generic[ModelType]):
    def __init__(self, data: Dict[Period, ModelType]):
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

    def items(self) -> Iterator[Tuple[Period, ModelType]]:
        return ((model.period, model.model) for model in self.models)

    def get_model(self, timestep: datetime) -> ModelType:
        for model in self.models:
            if timestep in model.period:
                return model.model

        raise ValueError(f"Model for timestep '{timestep}' not found in Temporal model")
