import abc
from datetime import datetime
from typing import Dict, Iterator, List, Optional, Protocol, Tuple, Union

from libecalc.common.units import Unit
from libecalc.domain.tabular.tabular import Tabular
from libecalc.presentation.exporter.formatters.exceptions import (
    IncompatibleData,
    IncorrectInput,
)

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


class Formatter(abc.ABC):
    @abc.abstractmethod
    def format(self, tabular: Formattable, header_prefix: str = None) -> List[str]:
        """

        Args:
            header_prefix: string that will be added to the header with a '.' between prefix and regular header. {header_prefix}.{header}
            tabular: the data that should be formatted

        Returns: formatted rows as a list of string

        """

    @abc.abstractmethod
    def format_many(self, formattables: Iterator[Tuple[str, Formattable]]) -> List[str]:
        """
        Combine several formattable objects into a single csv
        Args:
            formattables: list of tuples that should be formatted, the first item will be used as prefix in the resulting row headers.

        Returns:

        """


Rows = List[str]


class CSVFormatter(Formatter):
    def __init__(self, separation_character: str = ",", use_column_id_in_header: bool = False):
        """
        Format tabular data into rows
        Args:
            separation_character: the separator used between items in a row
            use_column_id_in_header: when True, a comment with column title and unit will be added instead of including it in the header
        """
        self.separation_character = separation_character
        self._use_column_id_in_header = use_column_id_in_header

    @staticmethod
    def _format_column_info(column: Column, header_prefix: Optional[str]) -> str:
        info_str = ""
        if header_prefix is not None:
            info_str += f"{header_prefix}."

        info_str += f"{column.title}"

        if hasattr(column, "unit"):
            info_str += f"[{column.unit}]"
        return info_str

    def _get_column_info_row(
        self, column_ids: List[ColumnIndex], columns: Dict[ColumnIndex, Column], header_prefix: Optional[str]
    ) -> str:
        return self.separation_character.join(
            [self._format_column_info(columns[column_id], header_prefix) for column_id in column_ids]
        )

    def _get_header(
        self, column_ids: List[ColumnIndex], columns: Dict[ColumnIndex, Column], header_prefix: Optional[str]
    ) -> List[str]:
        """
        Create the header rows.
        Returns: one or more header rows
        """
        if self._use_column_id_in_header:
            return [
                self.separation_character.join(list(column_ids)),
                "#" + self._get_column_info_row(column_ids, columns, header_prefix),
            ]
        else:
            return [self._get_column_info_row(column_ids, columns, header_prefix)]

    def format(self, tabular: Formattable, header_prefix: str = None) -> Rows:
        """

        Args:
            header_prefix: string that will be added to the header with a '.' between prefix and regular header. {header_prefix}.{header}
            tabular: the data that should be formatted

        Returns: formatted rows as a list of string

        """
        column_ids = tabular.column_ids
        columns = {column_id: tabular.get_column(column_id) for column_id in column_ids}

        rows: List[str] = self._get_header(column_ids, columns, header_prefix)

        for row_id in tabular.row_ids:
            row = [str(tabular.get_value(row_id, column_id)) for column_id in column_ids]
            rows.append(self.separation_character.join(row))
        return rows

    def format_many(self, formattables: Iterator[Tuple[str, Formattable]]) -> Rows:
        """
        Combine several formattable objects into a single csv
        Args:
            formattables: list of tuples that should be formatted, the first item will be used as prefix in the resulting row headers.

        Returns:

        """

        formatted = [self.format(tabular, header_prefix=name) for name, tabular in formattables]

        if len(formatted) == 0:
            raise IncorrectInput()
        elif len(formatted) == 1:
            return formatted[0]

        [first, *rest] = formatted

        if not all(len(rows) == len(first) for rows in rest):
            raise IncompatibleData()

        combined_rows = []
        for row_index in range(len(first)):
            separate_rows = [rows[row_index] for rows in formatted]
            combined_rows.append(self.separation_character.join(separate_rows))

        return combined_rows
