from abc import ABC, abstractmethod

from libecalc.common.time_utils import Period
from libecalc.dto.base import EcalcBaseModel
from typing_extensions import Self


class OperationalSettings(ABC, EcalcBaseModel):
    @abstractmethod
    def get_subset_from_period(self, period: Period) -> Self:
        ...
