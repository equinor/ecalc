from dataclasses import dataclass
from datetime import datetime
from typing import Self

from libecalc.common.time_utils import Period


@dataclass(eq=True, frozen=True)
class ModelChangeEvent:
    """
    An event that (might) change the structure of the diagram. Since dates in the model might be used to set
    expressions only, the structure might not change even though there is a change event.
    """

    name: str
    period: Period

    @property
    def start(self) -> datetime:
        return self.period.start

    @property
    def end(self) -> datetime:
        return self.period.end

    @classmethod
    def from_period(cls, period) -> Self:
        return cls(
            name=str(period.start),
            period=period,
        )
