import abc
from datetime import datetime
from typing import Dict, Iterator, List, Optional, Protocol, Tuple, Union

from libecalc.common.units import Unit
from libecalc.domain.tabular.tabular import Tabular

RowIndex = Union[str, int, float, datetime]
ColumnIndex = Union[str]


class ColumnWithoutUnit(Protocol):
    @property
    @abc.abstractmethod
    def title(self) -> str:
        ...


class ColumnWithUnit(ColumnWithoutUnit, Protocol):
    @property
    @abc.abstractmethod
    def unit(self) -> Optional[Unit]:
        ...


Column = Union[ColumnWithUnit, ColumnWithoutUnit]


class Formattable(Tabular[RowIndex, ColumnIndex], Protocol):
    @abc.abstractmethod
    def get_column(self, column_id: ColumnIndex) -> Column:
        ...


class FormattableGroup(Protocol):
    @property
    @abc.abstractmethod
    def groups(self) -> Iterator[Tuple[str, Formattable]]:
        ...


class Formatter(abc.ABC):
    @abc.abstractmethod
    def format(self, table: Formattable) -> List[str]:
        """Format data to line-based ascii/string based format. Rename once we add
        support for binary and other structures...
        :return:
        """
        ...

    @abc.abstractmethod
    def format_group(self, groups: FormattableGroup) -> Dict[str, List[str]]:
        ...


class CSVFormatter:
    def __init__(self, separation_character: str = ","):
        self.separation_character = separation_character

    @staticmethod
    def _format_column_info(column: Column) -> str:
        info_str = f"{column.title}"

        if hasattr(column, "unit"):
            info_str += f"[{column.unit}]"
        return info_str

    def format(self, tabular: Formattable) -> List[str]:
        column_ids = tabular.column_ids
        rows: List[str] = [
            self.separation_character.join(list(column_ids)),
            "#"
            + self.separation_character.join(
                [self._format_column_info(tabular.get_column(column_id)) for column_id in column_ids]
            ),
        ]

        for row_id in tabular.row_ids:
            row = [str(tabular.get_value(row_id, column_id)) for column_id in column_ids]
            rows.append(self.separation_character.join(row))
        return rows

    def format_groups(self, grouped_tabular: FormattableGroup) -> Dict[str, List[str]]:
        csv_formatted_lists_per_installation: Dict[str, List[str]] = {}
        for group_name, tabular in grouped_tabular.groups:
            csv_formatted_lists_per_installation[group_name] = self.format(tabular)
        return csv_formatted_lists_per_installation
