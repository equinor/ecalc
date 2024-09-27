from dataclasses import dataclass

from libecalc.common.time_utils import Periods
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
        periods: Periods,
    ) -> FilteredResult:
        query_result_collection = self.aggregator.aggregate(energy_calculator_result)

        return FilteredResult(query_results=query_result_collection, periods=periods)
