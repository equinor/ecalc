from libecalc.application.energy_calculator import EnergyCalculator
from libecalc.application.graph_result import EnergyCalculatorResult
from libecalc.fixtures import YamlCase


def test_example_models_validity(valid_example_case_yaml_case: YamlCase):
    """Test that all example models produce valid results.

    This test ensures that example models used in documentation (simple, advanced, drogon etc.)
    produce valid results when run. If this test fails, either:
    1. Someone has edited an example model incorrectly
    2. Code changes have made the model invalid and it needs updating
    """
    model = valid_example_case_yaml_case.get_yaml_model()

    # Validate model - will raise ModelValidationException if invalid
    model.validate_for_run()

    # Run calculations to ensure they complete without errors
    variables = model.variables
    energy_calculator = EnergyCalculator(energy_model=model, expression_evaluator=variables)
    consumer_results = energy_calculator.evaluate_energy_usage()
    emission_results = energy_calculator.evaluate_emissions()

    # Create result object
    result = EnergyCalculatorResult(
        consumer_results=consumer_results,
        variables_map=variables,
        emission_results=emission_results,
    )

    # Validate all components in consumer results
    for component_id, component_result in result.consumer_results.items():
        # Check main component
        try:
            assert all(
                component_result.component_result.is_valid.values
            ), f"Component {component_id} has invalid results"
        except AssertionError as e:
            print(f"Component {component_id} failed validation.")
            print(f"Component Result: {component_result.component_result}")
            print(f"is_valid list: {component_result.component_result.is_valid.values}")
            raise e

        # Check sub-components
        for sub_component in component_result.sub_components:
            try:
                assert all(
                    sub_component.is_valid.values
                ), f"Sub-component {sub_component.id} of {component_id} has invalid results"
            except AssertionError as e:
                print(f"Sub-component {sub_component.id} of {component_id} failed validation.")
                print(f"Sub-component Result: {sub_component}")
                print(f"is_valid list: {sub_component.is_valid.values}")
                raise e

        # Check models
        for model_result in component_result.models:
            try:
                assert all(
                    model_result.is_valid.values
                ), f"Model {model_result.id} in {component_id} has invalid results"
            except AssertionError as e:
                print(f"Model {model_result.id} in {component_id} failed validation.")
                print(f"Model Result: {model_result}")
                print(f"is_valid list: {model_result.is_valid.values}")
                raise e
