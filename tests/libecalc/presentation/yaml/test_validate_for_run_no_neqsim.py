from unittest.mock import patch

from ecalc_neqsim_wrapper import NeqsimService
from libecalc.fixtures import YamlCase


def test_validate_for_run_does_not_use_neqsim(all_energy_usage_models_yaml: YamlCase):
    """
    This test ensures that the validation workflow does not require neqsim.

    Background:
    During validate_for_run, neqsim should NOT be accessed because:
    - Validation should be fast to provide quick feedback when setting up eCalc models
    - Neqsim calculations are expensive and only needed during actual model runs
    - Validation workflow should check model structure without computing results

    History:
    - Issue discovered when Chart(...).curves was called during validation
    - For GENERIC_FROM_INPUT charts, accessing .curves triggers neqsim calculations
    - Fixed with a guard in Chart.__check_that_there_is_at_least_one_chart_curve()
    - This test ensures future code changes don't reintroduce Neqsim use
      as a part of the validation step.

    The test uses the all_energy_usage_models fixture because it covers:
    - Many different consumer types
    - Various chart types including GENERIC_FROM_INPUT
    - Comprehensive coverage of validation code paths
    """
    with patch.object(
        NeqsimService,
        "instance",
        side_effect=AssertionError(
            "NEQSIM SERVICE ACCESSED DURING VALIDATION!\n"
            "Neqsim service should NOT be accessed during validate_for_run.\n"
            "Only actual runs should use neqsim."
        ),
    ):
        model = all_energy_usage_models_yaml.get_yaml_model()

        # This should complete successfully without touching neqsim
        # If neqsim is accessed, the mock will raise AssertionError
        model.validate_for_run()
