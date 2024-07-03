from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Iterator, List, Tuple, Union

from libecalc.common.units import Unit
from libecalc.domain.tabular.exceptions import ColumnNotFound
from libecalc.presentation.exporter.formatters.formatter import (
    ColumnIndex,
    Formattable,
    FormattableGroup,
    RowIndex,
)


@dataclass
class DataSeries:
    name: str
    title: str
    values: List[Union[str, float]]

    def get_title(self) -> str:
        return self.title

    @property
    def id(self) -> str:
        return self.name


@dataclass
class QueryResult:
    """TODO: Generic result...can e.g. be datetime...or string?
    enough data in order to correctly format the results....

    TODO: provide more info e.g. on hierarchy etc? can also be done by having id and link to yaml...
    """

    name: str
    title: str
    unit: Unit  # Needed! in order to know how to handler further....parse
    values: Dict[datetime, float]

    def get_title(self) -> str:
        return f"{self.title}[{self.unit}]"

    @property
    def id(self) -> str:
        return self.name

    # TODO: split? we will at this level always have one time vector..?!


@dataclass
class GroupedQueryResult:
    group_name: str
    query_results: List[QueryResult]


@dataclass
class FormattableGroupedQuery(Formattable):
    data_series: List[DataSeries]
    query_results: List[QueryResult]
    time_vector: List[datetime]

    @property
    def row_ids(self) -> List[RowIndex]:
        return self.time_vector

    @property
    def column_ids(self) -> List[ColumnIndex]:
        column_ids = []
        for data_serie in self.data_series:
            column_ids.append(data_serie.id)
        for query_result in self.query_results:
            column_ids.append(query_result.id)
        return column_ids

    def get_column(self, column_id: ColumnIndex) -> Union[DataSeries, QueryResult]:
        try:
            return next(data_serie for data_serie in self.data_series if data_serie.id == column_id)
        except StopIteration:
            try:
                return next(query_result for query_result in self.query_results if query_result.id == column_id)
            except StopIteration as e:
                raise ColumnNotFound(column_id) from e

    def get_value(self, row_id: RowIndex, column_id: ColumnIndex) -> Union[int, float]:
        column = self.get_column(column_id)
        if isinstance(column, DataSeries):
            index = self.row_ids.index(row_id)
            return column.values[index]
        else:
            return column.values[row_id]


@dataclass
class FilteredResult(FormattableGroup):
    data_series: List[DataSeries]
    query_results: List[GroupedQueryResult]
    time_vector: List[datetime]

    @property
    def groups(self) -> Iterator[Tuple[str, Formattable]]:
        return (
            (
                group.group_name,
                FormattableGroupedQuery(
                    data_series=self.data_series,
                    time_vector=self.time_vector,
                    query_results=group.query_results,
                ),
            )
            for group in self.query_results
        )
