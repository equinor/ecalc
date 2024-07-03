from datetime import datetime

import pytest
from libecalc import dto
from libecalc.application.energy_calculator import EnergyCalculator
from libecalc.application.graph_result import GraphResult
from libecalc.common.units import Unit
from libecalc.common.utils.rates import RateType, TimeSeriesRate
from libecalc.presentation.json_result.mapper import get_asset_result


@pytest.fixture
def asset_with_two_installations(minimal_installation_dto_factory) -> dto.Asset:
    installation_1 = minimal_installation_dto_factory(installation_name="installaion1", fuel_rate=50)
    installation_2 = minimal_installation_dto_factory(installation_name="installaion2", fuel_rate=100)
    asset = dto.Asset(
        name="multiple_installations_asset",
        installations=[
            installation_1,
            installation_2,
        ],
    )
    return asset


def test_asset_with_multiple_installations(asset_with_two_installations):
    graph = asset_with_two_installations.get_graph()
    energy_calculator = EnergyCalculator(graph)
    timesteps = [datetime(2020, 1, 1), datetime(2021, 1, 1), datetime(2022, 1, 1)]
    variables_map = dto.VariablesMap(time_vector=timesteps)
    consumer_results = energy_calculator.evaluate_energy_usage(variables_map)
    emission_results = energy_calculator.evaluate_emissions(variables_map, consumer_results)
    graph_result = GraphResult(
        graph=graph,
        variables_map=variables_map,
        consumer_results=consumer_results,
        emission_results=emission_results,
    )

    asset_result = get_asset_result(graph_result)
    assert asset_result.component_result.energy_usage == TimeSeriesRate(
        values=[150, 150, 150],
        unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
        timesteps=timesteps,
        rate_type=RateType.CALENDAR_DAY,
        regularity=[1.0, 1.0, 1.0],
    )
