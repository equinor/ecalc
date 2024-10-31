import abc
from collections.abc import Iterator
from datetime import datetime
from typing import Protocol, Union

from libecalc.common.time_utils import Period
from libecalc.domain.tabular.tabular import HasColumns, Tabular


class Formattable(Tabular, HasColumns, Protocol): ...


class FormattableGroup(Protocol):
    @property
    @abc.abstractmethod
    def groups(self) -> Iterator[tuple[str, Formattable]]: ...


RowIndex = Union[str, int, float, datetime, Period]
ColumnIndex = Union[str]
