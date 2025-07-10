from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from datetime import datetime
from typing import Generic, Self, TypeVar

from libecalc.common.time_utils import Period, define_time_model_for_period

ModelType = TypeVar("ModelType")


class InvalidTemporalModel(Exception): ...


def _get_key_string(key: datetime | Period):
    if isinstance(key, datetime):
        return str(datetime)
    else:
        return str(key.start)


def _get_keys_message(keys: list[datetime | Period]) -> str:
    return ",".join(f"'{_get_key_string(key)}'" for key in keys)


class InvalidKeys(InvalidTemporalModel):
    def __init__(self, keys: list[datetime | Period]):
        # Message to user, only mention dates since we don't take Periods as input
        super().__init__(
            f"All keys must be dates on the format 'YYYY-MM-DD', e.g. '1969-12-23'. Got {_get_keys_message(keys)}."
        )


class UnsortedKeys(InvalidTemporalModel):
    def __init__(self, keys: list[datetime | Period]):
        # Message to user, only mention dates since we don't take Periods as input
        super().__init__(
            f"Dates in a temporal model should be sorted with the earliest date first. Got {_get_keys_message(keys)}"
        )


@dataclass
class Model(Generic[ModelType]):
    period: Period
    model: ModelType


class TemporalModel(Generic[ModelType]):
    """If data has datetime keys, convert to Period keys"""

    def __init__(self, data: dict[datetime, ModelType] | dict[Period, ModelType]):
        periods = []
        models = []
        if all(isinstance(key, datetime) for key in data.keys()):
            # convert date keys to Period keys
            model_dates: list[datetime] = list(data.keys()) + [datetime.max.replace(microsecond=0)]
            for start_time, end_time, model in zip(model_dates[:-1], model_dates[1:], data.values()):
                period = Period(
                    start=start_time,
                    end=end_time,
                )
                periods.append(period)
                models.append(
                    Model(
                        period=period,
                        model=model,
                    )
                )
        elif all(isinstance(key, Period) for key in data.keys()):
            for period, model in data.items():
                assert isinstance(period, Period)
                periods.append(period)
                models.append(
                    Model(
                        period=period,
                        model=model,
                    )
                )
        else:
            raise InvalidKeys(keys=list(data.keys()))

        self._periods: list[Period] = periods
        self._models: list[Model[ModelType]] = models

        if not (list(self._periods) == sorted(self._periods)):
            raise UnsortedKeys(keys=list(data.keys()))

    def get_models(self) -> Iterable[ModelType]:
        for model in self._models:
            yield model.model

    def get_periods(self) -> Iterable[Period]:
        return self._periods

    def items(self) -> Iterator[tuple[Period, ModelType]]:
        return ((model.period, model.model) for model in self._models)

    def get_model(self, period: Period | datetime) -> ModelType:
        for model in self._models:
            if period in model.period:
                return model.model

        raise ValueError(f"Model for timestep '{period}' not found in Temporal model")

    @classmethod
    def create(cls, data: ModelType | dict[datetime, ModelType], target_period: Period) -> Self | None:
        time_model = define_time_model_for_period(data, target_period)
        if time_model is None:
            return None

        return cls(time_model)
