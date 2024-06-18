import abc
from typing import Protocol, Dict, List

from libecalc.common.utils.rates import TimeSeries


class ResultSet(Protocol):

    @abc.abstractmethod
    def get_result_components(self) -> Dict[str, "ResultSet"]:
        ...

    @abc.abstractmethod
    def get_time_series(self) -> List[TimeSeries]:
        ...


class CSVBuilder:

    def __init__(self, separation_character: str = ','):
        self.separation_character = separation_character

    def add_(self, ):
