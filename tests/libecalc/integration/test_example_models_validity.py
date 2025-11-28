import pytest

from libecalc.fixtures import YamlCase


@pytest.fixture(
    scope="function",
    params=[
        ("simple", "simple_yaml"),
        ("simple_temporal", "simple_temporal_yaml"),
        ("advanced_sampled", "advanced_yaml_sampled"),  # Sampled timesteps for 75% faster testing
        ("drogon", "drogon_yaml"),
    ],
    ids=lambda param: param[0],
)
def examples_validity_testing_yaml_cases(request) -> YamlCase:
    """Parametrized fixture returning YamlCase for each example model.

    Tests all documented example models to ensure they remain valid as the codebase evolves.
    Uses sampled timesteps for the advanced model to keep test suite performant.
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
    model.evaluate_energy_usage()

    # Validate all components
    for component in model.get_energy_components():
        assert all(model.get_validity(component.id).values)
