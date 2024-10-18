import abc
from datetime import datetime
from typing import Iterator, Protocol, Tuple, Union

from libecalc.domain.tabular.tabular import HasColumns, Tabular


class Formattable(Tabular, HasColumns, Protocol): ...


class FormattableGroup(Protocol):
    @property
    @abc.abstractmethod
    def groups(self) -> Iterator[Tuple[str, Formattable]]: ...


RowIndex = Union[str, int, float, datetime]
ColumnIndex = Union[str]
