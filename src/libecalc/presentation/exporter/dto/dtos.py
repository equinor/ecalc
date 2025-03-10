from collections.abc import Iterator
from dataclasses import dataclass

from libecalc.common.time_utils import Period, Periods
from libecalc.common.units import Unit
from libecalc.domain.tabular.exceptions import ColumnNotFound
from libecalc.presentation.exporter.formatters.formattable import ColumnIndex, Formattable, FormattableGroup, RowIndex


@dataclass
class DataSeries:
    name: str
    title: str
    values: list[str | float]

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
    values: dict[Period, float]

    def get_title(self) -> str:
        return f"{self.title}[{self.unit}]"

    @property
    def id(self) -> str:
        return self.name

    # TODO: split? we will at this level always have one time vector..?!


@dataclass
class GroupedQueryResult:
    group_name: str
    query_results: list[QueryResult]


@dataclass
class FormattableGroupedQuery(Formattable):
    query_results: list[QueryResult]
    periods: Periods

    @property
    def row_ids(self) -> list[RowIndex]:
        return self.periods.periods

    @property
    def column_ids(self) -> list[ColumnIndex]:
        column_ids = []
        for query_result in self.query_results:
            column_ids.append(query_result.id)
        return column_ids

    def get_column(self, column_id: ColumnIndex) -> DataSeries | QueryResult:
        try:
            return next(query_result for query_result in self.query_results if query_result.id == column_id)
        except StopIteration as e:
            raise ColumnNotFound(column_id) from e

    def get_value(self, row_id: RowIndex, column_id: ColumnIndex) -> int | float:
        column = self.get_column(column_id)
        return column.values[row_id]


@dataclass
class FilteredResult(FormattableGroup):
    query_results: list[GroupedQueryResult]
    periods: Periods

    @property
    def groups(self) -> Iterator[tuple[str, Formattable]]:
        return (
            (
                group.group_name,
                FormattableGroupedQuery(
                    periods=self.periods,
                    query_results=group.query_results,
                ),
            )
            for group in self.query_results
        )
