from dataclasses import dataclass
from typing import Dict, Generic, Iterator, Tuple, TypeVar

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

    def items(self) -> Iterator[Tuple[Period, ModelType]]:
        return ((model.period, model.model) for model in self.models)

    def get_model(self, period: Period) -> ModelType:
        for model in self.models:
            if period in model.period:
                return model.model

        raise ValueError(f"Model for timestep '{period}' not found in Temporal model")
