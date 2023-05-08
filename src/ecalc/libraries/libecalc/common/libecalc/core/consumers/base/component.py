from abc import ABC, abstractmethod
from typing import List, Union

from libecalc.core.result import EcalcModelResult
from libecalc.dto import VariablesMap
from libecalc.dto.core_specs.compressor.operational_settings import (
    CompressorOperationalSettings,
)
from libecalc.dto.core_specs.pump.operational_settings import PumpOperationalSettings


class BaseConsumer(ABC):
    @abstractmethod
    def evaluate(
        self,
        variables_map: VariablesMap,
        temporal_operational_settings,
    ) -> EcalcModelResult:
        ...


class BaseConsumerWithoutOperationalSettings(ABC):
    id: str

    @property
    @abstractmethod
    def operational_settings(self):
        ...

    @abstractmethod
    def get_max_rate(
        self, operational_settings: Union[CompressorOperationalSettings, PumpOperationalSettings]
    ) -> List[float]:
        ...

    @abstractmethod
    def evaluate(self, **kwargs) -> EcalcModelResult:
        ...
