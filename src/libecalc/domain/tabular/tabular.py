import abc
from typing import List, Protocol, TypeVar, Union

ColumnIndex = TypeVar("ColumnIndex")
RowIndex = TypeVar("RowIndex")


class Tabular(Protocol[RowIndex, ColumnIndex]):
    @property
    @abc.abstractmethod
    def row_ids(self) -> List[RowIndex]:
        ...

    @property
    @abc.abstractmethod
    def column_ids(self) -> List[ColumnIndex]:
        ...

    @abc.abstractmethod
    def get_value(self, row_id: RowIndex, column_id: ColumnIndex) -> Union[int, float]:
        ...
