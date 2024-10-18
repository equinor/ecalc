from dataclasses import dataclass
from datetime import datetime
from typing import List

from libecalc.presentation.exporter.aggregators import Aggregator
from libecalc.presentation.exporter.domain.exportable import ExportableSet
from libecalc.presentation.exporter.dto.dtos import FilteredResult


@dataclass
class Filter:
    """A filter is a collection of all the settings required in order to filter
    the complete result object.
    """

    aggregator: Aggregator
    """
    Currently only one type of aggregator can be used, since we cannot deal with different levels of aggregators
    Currently we only aggregate/group at installation level. We will deal with future problems later.
    """

    def filter(
        self,
        energy_calculator_result: ExportableSet,
        time_vector: List[datetime],
    ) -> FilteredResult:
        query_result_collection = self.aggregator.aggregate(energy_calculator_result)

        return FilteredResult(query_results=query_result_collection, time_vector=time_vector)
