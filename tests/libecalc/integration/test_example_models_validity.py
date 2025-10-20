import pytest

from libecalc.fixtures import YamlCase


@pytest.fixture(
    scope="function",
    params=[
        ("simple", "simple_yaml"),
        ("simple_temporal", "simple_temporal_yaml"),
        ("advanced", "advanced_yaml"),
        ("drogon", "drogon_yaml"),
    ],
    ids=lambda param: param[0],
)
def examples_validity_testing_yaml_cases(request) -> YamlCase:
    """
    Parametrized fixture returning each YamlCase for the specified examples
    """
    yaml_case = request.getfixturevalue(request.param[1])
    return yaml_case


def test_example_models_validity(examples_validity_testing_yaml_cases: YamlCase):
    """Test that all example models produce valid results.

    This test ensures that example models used in documentation (simple, advanced, drogon etc.)
    produce valid results when run. If this test fails, either:
    1. Someone has edited an example model incorrectly
    2. Code changes have made the model invalid and it needs updating
    """
    model = examples_validity_testing_yaml_cases.get_yaml_model()

    # Validate model - will raise ModelValidationException if invalid
    model.validate_for_run()

    # Run calculations to ensure they complete without errors
    consumer_results = model.evaluate_energy_usage()

    # Validate all components in consumer results
    for component_id, component_result in consumer_results.items():
        # Check main component
        try:
            assert all(component_result.is_valid.values)
        except AssertionError as e:
            print(f"Component {component_id} failed validation.")
            print(f"Component Result: {component_result}")
            print(f"is_valid list: {component_result.is_valid.values}")
            raise e
