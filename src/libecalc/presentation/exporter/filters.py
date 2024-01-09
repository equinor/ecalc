from dataclasses import dataclass
from datetime import datetime
from typing import List

from libecalc.application.graph_result import GraphResult
from libecalc.presentation.exporter.aggregators import Aggregator
from libecalc.presentation.exporter.dto.dtos import FilteredResult
from libecalc.presentation.exporter.generators import Generator


@dataclass
class Filter:
    """A filter is a collection of all the settings required in order to filter
    the complete result object.
    """

    generators: List[Generator]
    """
    The index all the data relate to is a bit special...
    """

    aggregator: Aggregator
    """
    Currently only one type of aggregator can be used, since we cannot deal with different levels of aggregators
    Currently we only aggregate/group at installation level. We will deal with future problems later.
    """

    def filter(
        self,
        energy_calculator_result: GraphResult,
        time_vector: List[datetime],
    ) -> FilteredResult:
        data_series_collection = [
            generator.generate(energy_calculator_result, time_vector) for generator in self.generators
        ]
        query_result_collection = self.aggregator.aggregate(energy_calculator_result)

        return FilteredResult(
            data_series=data_series_collection, query_results=query_result_collection, time_vector=time_vector
        )
