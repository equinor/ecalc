import itertools
import json
from pathlib import Path

import pytest

from libecalc.application.energy_calculator import EnergyCalculator
from libecalc.application.graph_result import EnergyCalculatorResult
from libecalc.fixtures import YamlCase


def result(consumer_system_v2: YamlCase) -> EnergyCalculatorResult:
    model = consumer_system_v2.get_yaml_model()
    model.validate_for_run()
    variables = model.variables
    energy_calculator = EnergyCalculator(energy_model=model, expression_evaluator=variables)
    consumer_results = energy_calculator.evaluate_energy_usage()
    emission_results = energy_calculator.evaluate_emissions()

    return EnergyCalculatorResult(
        consumer_results=consumer_results,
        variables_map=variables,
        emission_results=emission_results,
    )


parameterized_v2_parameters = [
    (
        "consumer_system_v2",
        "consumer_system_v2_yaml",  # Fixture name
    ),
]


@pytest.mark.parametrize(
    "name, consumer_system_v2_fixture_name",
    parameterized_v2_parameters,
)
@pytest.mark.snapshot
def test_compressor_system_v2_results(name: str, consumer_system_v2_fixture_name: str, request):
    """
    NOTE: The test below depends on this test. If the order of parameters or names of the parameters are
    changed, the test below will fail. This test is meant to show that despite different permutations of
    temporal models for consumers (in a consumer system) or temporal operational settings, the results
    will/shall be the same.

    Overview of Consumer system v2 and how to get this done:

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
    consumer_system_v2 = request.getfixturevalue(consumer_system_v2_fixture_name)
    rounded_snapshot = request.getfixturevalue("rounded_snapshot")

    ecalc_result = result(consumer_system_v2)

    asset_graph = consumer_system_v2.get_yaml_model().get_graph()
    pump_system_id = asset_graph.get_node_id_by_name("pump_system")
    pump_system_v2_id = asset_graph.get_node_id_by_name("pump_system_v2")
    compressor_system_id = asset_graph.get_node_id_by_name("compressor_system")
    compressor_system_v2_id = asset_graph.get_node_id_by_name("compressor_system_v2")

    pump_system_result = ecalc_result.consumer_results[pump_system_id]
    pump_system_component_result = pump_system_result.component_result.model_copy(
        update={"operational_settings_results": None, "id": "pump system"}
    )
    pump_system_v2_result = ecalc_result.consumer_results[pump_system_v2_id]
    pump_system_v2_component_result = pump_system_v2_result.component_result.model_copy(
        update={"operational_settings_results": None, "id": "pump system"}
    )
    compressor_system_result = ecalc_result.consumer_results[compressor_system_id]
    compressor_system_component_result = compressor_system_result.component_result.model_copy(
        update={"operational_settings_results": None, "id": "compressor system"}
    )
    compressor_system_v2_result = ecalc_result.consumer_results[compressor_system_v2_id]
    compressor_system_v2_component_result = compressor_system_v2_result.component_result.model_copy(
        update={"operational_settings_results": None, "id": "compressor system"}
    )

    # assert actual expected
    assert compressor_system_component_result.power.unit == compressor_system_v2_component_result.power.unit
    assert isinstance(compressor_system_component_result.power, type(compressor_system_v2_component_result.power))

    assert pump_system_component_result.model_dump() == pump_system_v2_component_result.model_dump()
    assert compressor_system_component_result.model_dump() == compressor_system_v2_component_result.model_dump()

    snapshot_name = f"{name}.json"
    rounded_snapshot(data=ecalc_result.model_dump(), snapshot_name=snapshot_name)


def test_compare_snapshots(snapshot):
    """
    NOTE: This test depends on the test above. If you change order or names of the above tests, this will fail.
    This test is meant to show that despite different permutations of temporal models for consumers (in a consumer system) or temporal operational settings, the results
    will/shall be the same.

    Above, we generate snapshots for different scenarios wrt. temporal models etc. We should perhaps be able to
    compare those snapshots with each other...at least the "main result" should be comparable - since
    all the models above should yield the same results, but they are just using different temporal models ... but
    the temporal models have the same data
    :return:
    """

    consumer_system_v2_snapshots = []

    for case_name, fixture_name in parameterized_v2_parameters:
        print(f"testing {case_name}")
        # NOTE: When we use parameterized tests, there is some magic wrt. the name the snapshots are given, to make sure that they are 1. unique and 2. retrievable
        with open(
            Path(
                snapshot.snapshot_dir.parent
                / "test_compressor_system_v2_results"
                / f"{case_name}-{fixture_name}"
                / f"{case_name}.json"
            )
        ) as snapshot_file:
            consumer_system_v2_snapshots.append(json.loads(snapshot_file.read()))

    # Will generate pairs of all combinations of snapshots in order to compare all against each other for equality
    for a, b in itertools.combinations(consumer_system_v2_snapshots, 2):
        assert a == b
