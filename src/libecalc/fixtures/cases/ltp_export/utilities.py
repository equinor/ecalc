from datetime import datetime
from typing import List

from libecalc.application.energy_calculator import EnergyCalculator
from libecalc.application.graph_result import GraphResult
from libecalc.common.variables import VariablesMap
from libecalc.presentation.exporter.configs.configs import LTPConfig
from libecalc.presentation.yaml.model import YamlModel


def get_consumption(model: YamlModel, variables: VariablesMap, time_vector: List[datetime]):
    graph = model.get_graph()
    energy_calculator = EnergyCalculator(graph=graph)

    consumer_results = energy_calculator.evaluate_energy_usage()
    emission_results = energy_calculator.evaluate_emissions()

    graph_result = GraphResult(
        graph=graph,
        variables_map=variables,
        consumer_results=consumer_results,
        emission_results=emission_results,
    )

    ltp_filter = LTPConfig.filter(frequency=model.result_options.output_frequency)
    ltp_result = ltp_filter.filter(graph_result, time_vector)

    return ltp_result


def get_sum_ltp_column(ltp_result, installation_nr, ltp_column_nr) -> float:
    ltp_sum = sum(
        float(v) for (k, v) in ltp_result.query_results[installation_nr].query_results[ltp_column_nr].values.items()
    )
    return ltp_sum
