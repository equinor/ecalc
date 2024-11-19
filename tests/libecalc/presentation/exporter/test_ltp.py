from datetime import datetime
from pathlib import Path
from typing import Union

import pandas as pd

from libecalc import dto
from libecalc.application.energy_calculator import EnergyCalculator
from libecalc.application.graph_result import GraphResult
from libecalc.common.time_utils import Period
from libecalc.common.utils.rates import RateType
from libecalc.common.variables import VariablesMap
from libecalc.fixtures.cases import ltp_export
from libecalc.fixtures.cases.ltp_export.installation_setup import (
    installation_compressor_dto,
    simple_direct_el_consumer,
)
from libecalc.fixtures.cases.ltp_export.loading_storage_ltp_yaml import (
    ltp_oil_loaded_yaml_factory,
)
from libecalc.fixtures.cases.ltp_export.utilities import (
    get_consumption,
    get_sum_ltp_column,
)

from libecalc.presentation.json_result.mapper import get_asset_result

time_vector_installation = [
    datetime(2027, 1, 1),
    datetime(2027, 4, 10),
    datetime(2028, 1, 1),
    datetime(2028, 4, 10),
    datetime(2029, 1, 1),
]

time_vector_yearly = pd.date_range(datetime(2027, 1, 1), datetime(2029, 1, 1), freq="YS").to_pydatetime().tolist()


def calculate_asset_result(
    model: Union[dto.Installation, dto.Asset],
    variables: VariablesMap,
):
    model = model
    graph = model.get_graph()
    energy_calculator = EnergyCalculator(graph=graph)

    consumer_results = energy_calculator.evaluate_energy_usage(variables)
    emission_results = energy_calculator.evaluate_emissions(variables, consumer_results)

    results_core = GraphResult(
        graph=graph,
        variables_map=variables,
        consumer_results=consumer_results,
        emission_results=emission_results,
    )

    results_dto = get_asset_result(results_core)

    return results_dto


def test_electrical_and_mechanical_power_installation():
    """Check that new total power includes the sum of electrical- and mechanical power at installation level"""
    variables = VariablesMap(time_vector=time_vector_installation, variables={})
    asset = dto.Asset(
        name="Asset 1",
        installations=[
            installation_compressor_dto([simple_direct_el_consumer()]),
        ],
    )

    asset_result = calculate_asset_result(model=asset, variables=variables)
    power_fuel_driven_compressor = asset_result.get_component_by_name("compressor").power_cumulative.values[-1]
    power_generator_set = asset_result.get_component_by_name("genset").power_cumulative.values[-1]

    # Extract cumulative electrical-, mechanical- and total power.
    power_electrical_installation = asset_result.get_component_by_name(
        "INSTALLATION_A"
    ).power_electrical_cumulative.values[-1]

    power_mechanical_installation = asset_result.get_component_by_name(
        "INSTALLATION_A"
    ).power_mechanical_cumulative.values[-1]

    power_total_installation = asset_result.get_component_by_name("INSTALLATION_A").power_cumulative.values[-1]

    # Verify that total power is correct
    assert power_total_installation == power_electrical_installation + power_mechanical_installation

    # Verify that electrical power equals genset power, and mechanical power equals power from gas driven compressor:
    assert power_generator_set == power_electrical_installation
    assert power_fuel_driven_compressor == power_mechanical_installation


def test_electrical_and_mechanical_power_asset():
    """Check that new total power includes the sum of electrical- and mechanical power at installation level"""
    variables = VariablesMap(time_vector=time_vector_installation, variables={})
    installation_name_1 = "INSTALLATION_1"
    installation_name_2 = "INSTALLATION_2"

    asset = dto.Asset(
        name="Asset 1",
        installations=[
            installation_compressor_dto(
                [simple_direct_el_consumer(name="direct_el_consumer 1")],
                installation_name=installation_name_1,
                genset_name="generator 1",
                compressor_name="gas driven compressor 1",
            ),
            installation_compressor_dto(
                [simple_direct_el_consumer(name="direct_el_consumer 2")],
                installation_name=installation_name_2,
                genset_name="generator 2",
                compressor_name="gas driven compressor 2",
            ),
        ],
    )

    asset_result = calculate_asset_result(model=asset, variables=variables)
    power_electrical_installation_1 = asset_result.get_component_by_name(
        installation_name_1
    ).power_electrical_cumulative.values[-1]

    power_mechanical_installation_1 = asset_result.get_component_by_name(
        installation_name_1
    ).power_mechanical_cumulative.values[-1]

    power_electrical_installation_2 = asset_result.get_component_by_name(
        installation_name_2
    ).power_electrical_cumulative.values[-1]

    power_mechanical_installation_2 = asset_result.get_component_by_name(
        installation_name_2
    ).power_mechanical_cumulative.values[-1]

    asset_power_electrical = asset_result.get_component_by_name("Asset 1").power_electrical_cumulative.values[-1]

    asset_power_mechanical = asset_result.get_component_by_name("Asset 1").power_mechanical_cumulative.values[-1]

    # Verify that electrical power is correct at asset level
    assert asset_power_electrical == power_electrical_installation_1 + power_electrical_installation_2

    # Verify that mechanical power is correct at asset level:
    assert asset_power_mechanical == power_mechanical_installation_1 + power_mechanical_installation_2


def test_max_usage_from_shore(ltp_pfs_yaml_factory):
    """Test power from shore output for LTP export."""

    regularity = 0.2
    load = 10
    cable_loss = 0.1

    dto_case_csv = ltp_pfs_yaml_factory(
        regularity=regularity,
        cable_loss=cable_loss,
        max_usage_from_shore="MAX_USAGE_FROM_SHORE;MAX_USAGE_FROM_SHORE",
        load_direct_consumer=load,
        path=Path(ltp_export.__path__[0]),
    )

    ltp_result_csv = get_consumption(
        model=dto_case_csv.ecalc_model, variables=dto_case_csv.variables, periods=dto_case_csv.variables.get_periods()
    )

    max_usage_from_shore_2027 = float(
        ltp_result_csv.query_results[0].query_results[3].values[Period(datetime(2027, 1, 1), datetime(2028, 1, 1))]
    )

    # In the input csv-file max usage from shore is 250 (1.12.2026), 290 (1.6.2027), 283 (1.1.2028)
    # and 283 (1.1.2029). Ensure that the correct value is set for 2027 (290 from 1.6):
    assert max_usage_from_shore_2027 == 290.0

    # Ensure that values in 2027, 2028 and 2029 are correct, based on input file:
    assert [float(max_pfs) for max_pfs in ltp_result_csv.query_results[0].query_results[3].values.values()][2:5] == [
        290,
        283,
        283,
    ]
