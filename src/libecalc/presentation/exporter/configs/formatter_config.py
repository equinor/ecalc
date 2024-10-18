import abc
from typing import List

from libecalc.presentation.exporter.formatters.formatter import IndexFormatter
from libecalc.presentation.exporter.formatters.index_formatter import TimeIndexFormatter


class FormatterConfig(abc.ABC):
    @staticmethod
    @abc.abstractmethod
    def get_row_index_formatters() -> List[IndexFormatter]: ...


class TimeFormatterConfig(FormatterConfig):
    @staticmethod
    def get_row_index_formatters() -> List[IndexFormatter]:
        return [
            TimeIndexFormatter(
                name="forecastYear",
                title="Years",
                time_format="%Y",
            ),
            TimeIndexFormatter(
                name="forecastMonth",
                title="Months",
                time_format="%m",
            ),
        ]
