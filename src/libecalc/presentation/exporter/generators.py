import abc

from libecalc.common.time_utils import Periods
from libecalc.presentation.exporter.dto.dtos import DataSeries


class Generator(abc.ABC):
    @abc.abstractmethod
    def generate(
        self,
        periods: Periods,
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
        periods: Periods,
    ) -> DataSeries:
        return DataSeries(
            name=self.name,
            title=self.title,
            values=[str(period) for period in periods],
        )
