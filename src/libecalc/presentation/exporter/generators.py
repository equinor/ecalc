import abc
from datetime import datetime
from typing import List

from libecalc.application.graph_result import GraphResult
from libecalc.dto.result import EcalcModelResult
from libecalc.presentation.exporter.dto.dtos import DataSeries


class Generator(abc.ABC):
    @abc.abstractmethod
    def generate(
        self,
        energy_calculator_result: GraphResult,
        time_vector: List[datetime],
    ) -> DataSeries:
        pass


class TimeIndexGenerator(Generator):
    def __init__(
        self,
        name: str,
        title: str,
        time_format: str,
    ):
        self.name = name
        self.title = title
        self.time_format = time_format  # TODO: Correct to set here? is related to time_vector and frequency...

    def generate(
        self,
        energy_calculator_result: EcalcModelResult,
        time_vector: List[datetime],
    ) -> DataSeries:
        return DataSeries(
            name=self.name,
            title=self.title,
            values=[datetime.strftime(time_step, self.time_format) for time_step in time_vector],
        )
