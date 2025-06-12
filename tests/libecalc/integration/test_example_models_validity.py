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
            assert all(component_result.component_result.is_valid.values)
        except AssertionError as e:
            print(f"Component {component_id} failed validation.")
            print(f"Component Result: {component_result.component_result}")
            print(f"is_valid list: {component_result.component_result.is_valid.values}")
            raise e

        # Check sub-components
        for sub_component in component_result.sub_components:
            try:
                assert all(sub_component.is_valid.values)
            except AssertionError as e:
                print(f"Sub-component {sub_component.id} of {component_id} failed validation.")
                print(f"Sub-component Result: {sub_component}")
                print(f"is_valid list: {sub_component.is_valid.values}")
                raise e

        # Check models
        for model_result in component_result.models:
            try:
                assert all(model_result.is_valid.values)
            except AssertionError as e:
                print(f"Model {model_result.id} in {component_id} failed validation.")
                print(f"Model Result: {model_result}")
                print(f"is_valid list: {model_result.is_valid.values}")
                raise e
