import numpy as np

from libecalc.domain.infrastructure.energy_components.legacy_consumer.system.results import (
    ConsumerSystemComponentResult,
    ConsumerSystemConsumerFunctionResult,
    ConsumerSystemOperationalSettingResult,
)


class TestConsumerSystemComponentResult:
    def test_init(self, pump_model_result):
        component_result = ConsumerSystemComponentResult(
            name="some-model-name",
            consumer_model_result=pump_model_result,
        )

        np.testing.assert_allclose(component_result.energy_usage, [1, 2, 3])
        np.testing.assert_allclose(component_result.power, [1, 2, 3])
        np.testing.assert_allclose(component_result.rate, [1, 2, 3])


class TestConsumerSystemOperationalSettingResult:
    def test_valid_indices(self, compressor_model_result, compressor_model_result_invalid_steps):
        result_consumer_1 = ConsumerSystemComponentResult(
            name="some-model-name",
            consumer_model_result=compressor_model_result,
        )
        result_consumer_2 = ConsumerSystemComponentResult(
            name="some-model-name",
            consumer_model_result=compressor_model_result_invalid_steps,
        )

        operational_setting_result = ConsumerSystemOperationalSettingResult(
            consumer_results=[result_consumer_1, result_consumer_2],
        )

        # Timestep 1 in consumer 2 is invalid. Other than that everything is valid.
        assert operational_setting_result.indices_outside_capacity.tolist() == [1]
        assert operational_setting_result.indices_within_capacity.tolist() == [0, 2]


class TestConsumerSystemConsumerFunctionResult:
    def test_init(self, consumer_system_result: ConsumerSystemConsumerFunctionResult):
        assert consumer_system_result.energy_usage.tolist() == [1, 2, 3]

    def test_append(self, consumer_system_result):
        appended_consumer_system_result = consumer_system_result.extend(consumer_system_result)

        assert len(appended_consumer_system_result.periods) == 6
        assert np.all(appended_consumer_system_result.is_valid)
        assert appended_consumer_system_result.energy_usage.tolist() == [1, 2, 3, 1, 2, 3]
        assert appended_consumer_system_result.energy_usage_before_power_loss_factor.tolist() == [1, 2, 3, 1, 2, 3]
        assert appended_consumer_system_result.condition.tolist() == [1, 2, 3, 1, 2, 3]
        assert appended_consumer_system_result.power_loss_factor.tolist() == [1, 2, 3, 1, 2, 3]
        assert appended_consumer_system_result.energy_function_result is None
        assert appended_consumer_system_result.power.tolist() == [1, 2, 3, 1, 2, 3]
        assert isinstance(appended_consumer_system_result.operational_settings, list)
        assert isinstance(appended_consumer_system_result.operational_settings_results, list)
        assert isinstance(appended_consumer_system_result.consumer_results, list)
        assert appended_consumer_system_result.cross_over_used is None
