import abc
from typing import Protocol, TypeVar

ColumnIndex = TypeVar("ColumnIndex")
RowIndex = TypeVar("RowIndex")

TValue = TypeVar("TValue", covariant=True)


class Tabular(Protocol[RowIndex, ColumnIndex, TValue]):
    @property
    @abc.abstractmethod
    def row_ids(self) -> list[RowIndex]: ...

    @property
    @abc.abstractmethod
    def column_ids(self) -> list[ColumnIndex]: ...

    @abc.abstractmethod
    def get_value(self, row_id: RowIndex, column_id: ColumnIndex) -> TValue: ...


class Column(Protocol):
    @abc.abstractmethod
    def get_title(self) -> str: ...


TColumn = TypeVar("TColumn", bound=Column, covariant=True)


class HasColumns(Protocol[TColumn]):
    @abc.abstractmethod
    def get_column(self, column_id: ColumnIndex) -> TColumn: ...
