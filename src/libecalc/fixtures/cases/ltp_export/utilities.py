from typing import Union

from libecalc.application.energy_calculator import EnergyCalculator
from libecalc.application.graph_result import GraphResult
from libecalc.common.time_utils import Frequency, Periods
from libecalc.common.variables import VariablesMap
from libecalc.dto import Asset, Installation
from libecalc.presentation.exporter.configs.configs import LTPConfig
from libecalc.presentation.exporter.dto.dtos import FilteredResult
from libecalc.presentation.exporter.infrastructure import ExportableGraphResult


def get_consumption(model: Union[Installation, Asset], variables: VariablesMap, periods: Periods) -> FilteredResult:
    model = model
    graph = model.get_graph()
    energy_calculator = EnergyCalculator(graph=graph)

    consumer_results = energy_calculator.evaluate_energy_usage(variables)
    emission_results = energy_calculator.evaluate_emissions(variables, consumer_results)

    graph_result = GraphResult(
        graph=graph,
        variables_map=variables,
        consumer_results=consumer_results,
        emission_results=emission_results,
    )

    ltp_filter = LTPConfig.filter(frequency=Frequency.YEAR)
    ltp_result = ltp_filter.filter(ExportableGraphResult(graph_result), periods)

    return ltp_result


def get_sum_ltp_column(ltp_result: FilteredResult, installation_nr, ltp_column: str) -> float:
    installation_query_results = ltp_result.query_results[installation_nr].query_results
    column = [column for column in installation_query_results if column.id == ltp_column][0]

    ltp_sum = sum(float(v) for (k, v) in column.values.items())
    return ltp_sum
