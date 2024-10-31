import abc

from libecalc.presentation.exporter.formatters.formatter import IndexFormatter
from libecalc.presentation.exporter.formatters.index_formatter import PeriodIndexFormatter, TimeIndexFormatter


class FormatterConfig(abc.ABC):
    @staticmethod
    @abc.abstractmethod
    def get_row_index_formatters() -> list[IndexFormatter]: ...


class TimeFormatterConfig(FormatterConfig):
    @staticmethod
    def get_row_index_formatters() -> list[IndexFormatter]:
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


class PeriodFormatterConfig(FormatterConfig):
    @staticmethod
    def get_row_index_formatters() -> list[IndexFormatter]:
        return [
            PeriodIndexFormatter(
                name="forecastYear",
                title="Years",
                time_format="%Y",
            ),
            PeriodIndexFormatter(
                name="forecastMonth",
                title="Months",
                time_format="%m",
            ),
        ]
