from abc import ABC, abstractmethod
from datetime import datetime

from libecalc.dto.base import EcalcBaseModel
from typing_extensions import Self


class OperationalSettings(ABC, EcalcBaseModel):
    @abstractmethod
    def get_subset_for_timestep(self, timestep: datetime) -> Self:
        ...
