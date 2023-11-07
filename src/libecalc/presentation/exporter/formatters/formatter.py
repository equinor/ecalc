import abc
from typing import Dict, List

from libecalc.presentation.exporter.dto.dtos import FilteredResult


class Formatter(abc.ABC):
    @abc.abstractmethod
    def format(self, filtered_result: FilteredResult) -> Dict[str, List[str]]:
        """Format data to line-based ascii/string based format. Rename once we add
        support for binary and other structures...
        :return:
        """
        pass


class CSVFormatter(Formatter):
    """TODO: Should be agnostic about result, and just
    get e.g a pandas dataframe or a "column based serializeable".
    """

    def __init__(self, separation_character: str = ","):
        self.separation_character = separation_character

    def format(self, filtered_result: FilteredResult) -> Dict[str, List[str]]:
        """TODO: opposite wrapping, in order to inject this to config..instead
            the result and the mapper should only be added to the inner most class...then we just call what we have injected...
            instead of sending it down....

        TODO: Better with pandas implementation...?! or mirror the dict before doing this...
        """
        csv_formatted_lists_per_installation: Dict[str, List[str]] = {}
        # TODO: For each aggregator...or disallow for csv...
        for installation_result in filtered_result.query_results:
            csv_formatted_results: List[str] = []

            # headers
            # TODO: This column is _just_ as much defined as well, ie the format of this...a part of config/definition..
            csv_formatted_results.append(
                self.separation_character.join([data_result.name for data_result in filtered_result.data_series])
                + self.separation_character
                + self.separation_character.join(
                    [single_result.name for single_result in installation_result.query_results]
                )
            )
            csv_formatted_results.append(
                "#"
                + self.separation_character.join(
                    [f"{data_result.title}" for data_result in filtered_result.data_series]
                )
                + self.separation_character
                + self.separation_character.join(
                    [
                        f"{single_result.title}[{single_result.unit.value}]"
                        for single_result in installation_result.query_results
                    ]
                )
            )

            for index, time in enumerate(filtered_result.time_vector):
                csv_formatted_results.append(
                    self.separation_character.join(
                        [str(data_result.values[index]) for data_result in filtered_result.data_series]
                    )
                    + self.separation_character
                    + self.separation_character.join(
                        [str(single_result.values[time]) for single_result in installation_result.query_results]
                    )
                )

            csv_formatted_lists_per_installation[installation_result.group_name] = csv_formatted_results

        return csv_formatted_lists_per_installation
