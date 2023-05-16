import pytest
from libecalc.core.ecalc import EnergyCalculator
from libecalc.core.graph_result import EnergyCalculatorResult, GraphResult
from libecalc.fixtures import DTOCase


@pytest.fixture
def result(consumer_system_v2_dto) -> EnergyCalculatorResult:
    ecalc_model = consumer_system_v2_dto.ecalc_model
    variables = consumer_system_v2_dto.variables

    graph = ecalc_model.get_graph()
    energy_calculator = EnergyCalculator(graph=graph)
    consumer_results = energy_calculator.evaluate_energy_usage(variables)
    emission_results = energy_calculator.evaluate_emissions(
        variables_map=variables,
        consumer_results=consumer_results,
    )
    result = GraphResult(
        graph=graph,
        consumer_results=consumer_results,
        variables_map=variables,
        emission_results=emission_results,
    ).get_results()

    return result


@pytest.mark.snapshot
def test_compressor_system_v2_results(
    result: EnergyCalculatorResult, rounded_snapshot, consumer_system_v2_dto: DTOCase
):
    """Overview of Consumer system v2 and how to get this done:

    1. Get this test to run
        We've done breaking changes in v8 that did not get fixed in consumer system v2 due to this test being
        marked as pytest.mark.xfail.
    2. Add model results to the result object
        Currently we return model=[]. We need to figure out how to get the correct model results.
        We are also missing the specific results per operational setting for each model. This will break the
        EcalcModelResult-structure unless you come up with something clever
    3. Compare results with old consumer systems
        Create a similar test case for consumer system v1 and compare the results.
    4. Ensure that the output structure is Okay (LTP, CSV, JSON,...)
    5. Make FE compatible

    Then we need to document consumer system v2 and get feedback as soon as possible from the users. Mainly we want
    feedback on the YAML syntax and the result structure.

    Note: Consumer system v2 for pump and compressor are very similar. We should consider if they can share most
    of the code. Right now we duplicate code.
    """
    asset_graph = consumer_system_v2_dto.ecalc_model.get_graph()
    pump_system_id = asset_graph.get_component_id_by_name("pump_system")
    pump_system_v2_id = asset_graph.get_component_id_by_name("pump_system_v2")
    compressor_system_id = asset_graph.get_component_id_by_name("compressor_system")
    compressor_system_v2_id = asset_graph.get_component_id_by_name("compressor_system_v2")

    pump_system_result = result.consumer_results[pump_system_id].component_result.copy(
        update={"operational_settings_results": None, "id": "pump system"}
    )
    pump_system_v2_result = result.consumer_results[pump_system_v2_id].component_result.copy(
        update={"id": "pump system"}
    )
    compressor_system_result = result.consumer_results[compressor_system_id].component_result.copy(
        update={"operational_settings_results": None, "id": "compressor system"}
    )
    compressor_system_v2_result = result.consumer_results[compressor_system_v2_id].component_result.copy(
        update={"id": "compressor system"}
    )
    assert compressor_system_result.power.unit == compressor_system_v2_result.power.unit

    assert isinstance(compressor_system_result.power, type(compressor_system_v2_result.power))

    assert pump_system_v2_result.dict() == pump_system_result.dict()
    assert compressor_system_v2_result.dict() == compressor_system_result.dict()
    assert compressor_system_result.power == compressor_system_v2_result.power
    assert compressor_system_result.energy_usage == compressor_system_v2_result.energy_usage

    assert compressor_system_result.is_valid == compressor_system_v2_result.is_valid

    # emission result

    snapshot_name = "consumer_system_v2.json"
    rounded_snapshot(data=result.dict(), snapshot_name=snapshot_name)
