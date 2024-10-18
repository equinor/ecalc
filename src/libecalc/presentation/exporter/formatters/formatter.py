import abc
from typing import Dict, List

from libecalc.presentation.exporter.formatters.formattable import Formattable, FormattableGroup
from libecalc.presentation.exporter.formatters.index_formatter import IndexFormatter


class Formatter(abc.ABC):
    @abc.abstractmethod
    def format(self, table: Formattable) -> List[str]:
        """Format data to line-based ascii/string based format. Rename once we add
        support for binary and other structures...
        :return:
        """
        ...

    @abc.abstractmethod
    def format_group(self, groups: FormattableGroup) -> Dict[str, List[str]]: ...


class CSVFormatter:
    def __init__(self, separation_character: str = ",", index_formatters: List[IndexFormatter] = None):
        self.separation_character = separation_character
        self.index_formatters = index_formatters or []

    def format(self, tabular: Formattable) -> List[str]:
        column_ids = tabular.column_ids
        rows: List[str] = [
            self.separation_character.join(
                [*[index_formatter.get_id() for index_formatter in self.index_formatters], *column_ids]
            ),
            "#"
            + self.separation_character.join(
                [
                    *[index_formatter.get_title() for index_formatter in self.index_formatters],
                    *[tabular.get_column(column_id).get_title() for column_id in column_ids],
                ]
            ),
        ]

        for row_id in tabular.row_ids:
            row_index = [index_formatter.format(row_id) for index_formatter in self.index_formatters]
            row = [str(tabular.get_value(row_id, column_id)) for column_id in column_ids]
            rows.append(self.separation_character.join([*row_index, *row]))
        return rows

    def format_groups(self, grouped_tabular: FormattableGroup) -> Dict[str, List[str]]:
        csv_formatted_lists_per_installation: Dict[str, List[str]] = {}
        for group_name, tabular in grouped_tabular.groups:
            csv_formatted_lists_per_installation[group_name] = self.format(tabular)
        return csv_formatted_lists_per_installation
