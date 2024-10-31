from abc import ABC, abstractmethod
from datetime import datetime
from typing import Self

from libecalc.dto.base import EcalcBaseModel


class OperationalSettings(ABC, EcalcBaseModel):
    @abstractmethod
    def get_subset_for_timestep(self, timestep: datetime) -> Self: ...
