import abc
from datetime import datetime

from libecalc.common.time_utils import Period
from libecalc.presentation.exporter.formatters.formattable import RowIndex


class IndexFormatter(abc.ABC):
    """
    Index formatter can be used to format the index in a Formatter
    """

    @abc.abstractmethod
    def format(self, index: RowIndex) -> str: ...

    @abc.abstractmethod
    def get_title(self) -> str: ...

    @abc.abstractmethod
    def get_id(self) -> str: ...


class TimeIndexFormatter(IndexFormatter):
    def __init__(
        self,
        name: str,
        title: str,
        time_format: str,
    ):
        self.name = name
        self.title = title
        self.time_format = time_format

    def get_id(self) -> str:
        return self.name

    def get_title(self) -> str:
        return self.title

    def format(self, index: datetime) -> str:
        return datetime.strftime(index, self.time_format)


class PeriodIndexFormatter(IndexFormatter):
    def __init__(
        self,
        name: str,
        title: str,
        time_format: str,
    ):
        self.name = name
        self.title = title
        self.time_format = time_format

    def get_id(self) -> str:
        return self.name

    def get_title(self) -> str:
        return self.title

    def format(self, index: Period) -> str:
        return datetime.strftime(index.start, self.time_format)
