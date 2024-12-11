from datetime import datetime
from unittest.mock import Mock, patch

import numpy as np
import pandas as pd
import pytest

from libecalc.common.errors.exceptions import EcalcError
from libecalc.common.serializable_chart import SingleSpeedChartDTO
from libecalc.common.variables import VariablesMap
from libecalc.infrastructure.energy_components.legacy_consumer.consumer_function.pump_consumer_function import (
    PumpConsumerFunction,
)
from libecalc.infrastructure.energy_components.legacy_consumer.system.consumer_function import (
    CompressorSystemConsumerFunction,
    ConsumerSystemConsumerFunction,
    PumpSystemConsumerFunction,
)
from libecalc.infrastructure.energy_components.legacy_consumer.system.operational_setting import (
    CompressorSystemOperationalSetting,
    CompressorSystemOperationalSettingExpressions,
    ConsumerSystemOperationalSettingExpressions,
    PumpSystemOperationalSetting,
    PumpSystemOperationalSettingExpressions,
)
from libecalc.infrastructure.energy_components.legacy_consumer.system.types import ConsumerSystemComponent
from libecalc.core.models.chart import SingleSpeedChart
from libecalc.core.models.pump import PumpSingleSpeed
from libecalc.expression import Expression


@pytest.fixture
def consumer_system_variables_map():
    time_vector = [
        datetime(2020, 1, 1),
        datetime(2021, 1, 1),
        datetime(2022, 1, 1),
    ]
    return VariablesMap(
        variables={},
        time_vector=time_vector,
    )


@patch.multiple(ConsumerSystemConsumerFunction, __abstractmethods__=set())
class TestConsumerSystemConsumerFunction:
    def test_consumer_system(self):
        """Test init compressor system with mock expressions in consumer system.

        We want to make sure that we can initialize a consumer system if number of consumers match with
        the number of consumers in the operational settings expressions. I.e. the number of expressions for each
        timestep.
        """
        mock_consumer_component = Mock(ConsumerSystemComponent)
        mock_operational_setting_expressions = ConsumerSystemOperationalSettingExpressions(
            rates=[Mock(Expression)],
            suction_pressures=[Mock(Expression)],
            discharge_pressures=[Mock(Expression)],
        )
        consumer_system = ConsumerSystemConsumerFunction(
            consumer_components=[mock_consumer_component],
            operational_settings_expressions=[mock_operational_setting_expressions],
            condition_expression=None,
            power_loss_factor_expression=None,
        )

        assert consumer_system.number_of_consumers == 1
        assert consumer_system.condition_expression is None
        assert consumer_system.power_loss_factor_expression is None

    def test_consumer_system_mismatch_operational_settings(self):
        """Same as above but mismatch between operational settings and number of consumers."""
        mock_consumer_component = Mock(ConsumerSystemComponent)
        mock_operational_setting_expressions = ConsumerSystemOperationalSettingExpressions(
            rates=[Mock(Expression)],
            suction_pressures=[Mock(Expression)],
            discharge_pressures=[Mock(Expression)],
        )

        with pytest.raises(EcalcError) as err:
            ConsumerSystemConsumerFunction(
                consumer_components=[mock_consumer_component] * 2,
                operational_settings_expressions=[mock_operational_setting_expressions],
                condition_expression=None,
                power_loss_factor_expression=None,
            )

            assert (
                "Incompatible Data: Number of consumers in operational setting (1)"
                " does not match the number of consumers in the consumer system (2)" == str(err)
            )

    def test_consumer_system_two_consumers(self):
        mock_consumer_component = Mock(ConsumerSystemComponent)
        mock_operational_setting_expressions = ConsumerSystemOperationalSettingExpressions(
            rates=[Mock(Expression)] * 2,
            suction_pressures=[Mock(Expression)] * 2,
            discharge_pressures=[Mock(Expression)] * 2,
        )
        consumer_system = ConsumerSystemConsumerFunction(
            consumer_components=[mock_consumer_component] * 2,
            operational_settings_expressions=[mock_operational_setting_expressions],
            condition_expression=None,
            power_loss_factor_expression=None,
        )

        assert consumer_system.number_of_consumers == 2
        assert consumer_system.condition_expression is None
        assert consumer_system.power_loss_factor_expression is None

    def test_calculate_crossovers(self, pump_system):
        """Check that cross-overs works as expected."""
        consumer_system = pump_system

        # One time-step
        operational_setting = PumpSystemOperationalSetting(
            rates=[np.array([10000.0, 20000.0]), np.array([100.0, 1000.0])],
            suction_pressures=[np.array([1.0, 1.0]), np.array([1.0, 1.0])],
            discharge_pressures=[np.array([100.0, 100.0]), np.array([100.0, 100.0])],
            cross_overs=[2, 0],
            fluid_densities=[np.array([1000.0, 1000.0]), np.array([1000.0, 1000.0])],
        )

        operational_setting_after_cross_over = consumer_system.get_operational_settings_adjusted_for_cross_over(
            operational_settings=[operational_setting]
        )[0]

        results_before_cross_over = consumer_system.evaluate_consumers(
            operational_setting=operational_setting,
        )

        results_after_cross_over = consumer_system.evaluate_consumers(
            operational_setting=operational_setting_after_cross_over,
        )

        assert np.all(results_after_cross_over[0].rate < results_before_cross_over[0].rate)
        assert np.all(results_after_cross_over[1].rate > results_before_cross_over[1].rate)

        assert np.all(results_after_cross_over[1].energy_usage > results_before_cross_over[1].energy_usage)
        assert np.all(np.isnan(results_before_cross_over[0].energy_usage[1]))
        assert not np.any(np.isnan(results_after_cross_over[0].energy_usage))

        assert operational_setting_after_cross_over.rates[0][1] < operational_setting.rates[0][1]

    def test_calculate_rates_after_cross_over(self, pump_system):
        """Check that rates after cross-over are calculated correctly."""
        consumer_system = pump_system

        # One time-step
        operational_setting = PumpSystemOperationalSetting(
            rates=[np.array([20000.0]), np.array([100.0])],
            suction_pressures=[np.array([1.0]), np.array([1.0])],
            discharge_pressures=[np.array([100]), np.array([100.0])],
            cross_overs=[2, 0],
            fluid_densities=[np.array([1000.0]), np.array([1000.0])],
        )

        operational_settings_after_cross_over = consumer_system.calculate_operational_settings_after_cross_over(
            operational_setting=operational_setting
        )

        assert operational_settings_after_cross_over.rates[0][0] == pytest.approx(12007, rel=0.01)
        assert operational_settings_after_cross_over.rates[1][0] == pytest.approx(8092, rel=0.01)

    def test_calculate_rates_after_cross_over_compressor_system(self, compressor_system_sampled_2):
        """Check that rates after cross-over are calculated correctly."""
        consumer_system = compressor_system_sampled_2

        # One time-step
        operational_setting = CompressorSystemOperationalSetting(
            rates=[np.array([2000000.0]), np.array([2000000.0])],
            suction_pressures=[np.array([10.0]), np.array([10.0])],
            discharge_pressures=[np.array([20]), np.array([20.0])],
            cross_overs=[2, 0],
        )

        rates_after_cross_over = consumer_system.calculate_operational_settings_after_cross_over(
            operational_setting=operational_setting
        ).rates

        assert rates_after_cross_over[0][0] == pytest.approx(2.0, rel=0.01)
        assert rates_after_cross_over[1][0] == pytest.approx(3999998.0, rel=0.01)

    def test_get_cross_over_used(self):
        operational_setting_used_without_cross_over = CompressorSystemOperationalSetting(
            rates=[np.array([10000.0, 20000.0]), np.array([100.0, 1000.0])],
            suction_pressures=[np.array([10.0]), np.array([10.0])],
            discharge_pressures=[np.array([20]), np.array([20.0])],
            cross_overs=[2, 0],
        )

        operational_setting_used = CompressorSystemOperationalSetting(
            rates=[np.array([10000.0, 12000.0]), np.array([100.0, 9000.0])],
            suction_pressures=[np.array([10.0]), np.array([10.0])],
            discharge_pressures=[np.array([20]), np.array([20.0])],
            cross_overs=[2, 0],
        )

        cross_over_used = ConsumerSystemConsumerFunction.get_cross_over_used(
            operational_setting_used_without_cross_over=operational_setting_used_without_cross_over,
            operational_settings_used=operational_setting_used,
        )

        assert cross_over_used.tolist() == [0, 1]


class TestPumpSystemConsumerFunction:
    def test_pump_system_regularity(self, pump_system, consumer_system_variables_map):
        """Regularity only affects the rate: rate_stream_day = rate_calendar_day / regularity,
        regularity is between 0 and 1 (fraction of "full time").

        """
        operational_settings_expressions_evaluated = pump_system.get_operational_settings_from_expressions(
            expression_evaluator=consumer_system_variables_map,
            regularity=[1.0] * consumer_system_variables_map.number_of_periods,
        )

        operational_settings_expressions_evaluated_with_regularity = (
            pump_system.get_operational_settings_from_expressions(
                expression_evaluator=consumer_system_variables_map,
                regularity=[0.9] * consumer_system_variables_map.number_of_periods,
            )
        )

        np.testing.assert_allclose(
            operational_settings_expressions_evaluated_with_regularity[0].rates,
            np.divide(operational_settings_expressions_evaluated[0].rates, 0.9),
        )

    def test_evaluate_evaluate_operational_setting_expressions(self, pump_system):
        result = pump_system.evaluate_operational_setting_expressions(
            operational_setting_expressions=pump_system.operational_settings_expressions[0],
            expression_evaluator=VariablesMap(
                variables={
                    "SIM1;OIL_PROD_TOTAL": [25467.30664, 63761.23828, 145408.54688],
                    "SIM1;OIL_PROD_RATE": [2829.70068, 7658.78613, 10205.91406],
                },
                time_vector=[
                    datetime(1995, 10, 18, 0, 0),
                    datetime(1995, 10, 27, 0, 0),
                    datetime(1995, 11, 1, 0, 0),
                    datetime(1995, 11, 9, 0, 0),
                ],
            ),
        )

        assert result.rates[0].tolist() == [1, 1, 1]
        assert result.suction_pressures[0].tolist() == [1, 1, 1]
        assert result.discharge_pressures[0].tolist() == [2, 2, 2]

    def test_evaluate_consumers(self, pump_system):
        operational_settings = PumpSystemOperationalSetting(
            rates=[np.array([500.0, 500.0, 500.0]), np.array([500.0, 500.0, 500.0])],
            suction_pressures=[np.array([10.0, 10.0, 10.0]), np.array([10.0, 10.0, 10.0])],
            discharge_pressures=[np.array([20.0, 20.0, 20.0]), np.array([20.0, 20.0, 20.0])],
            cross_overs=None,
            fluid_densities=[np.array([1000.0, 1000.0, 1000.0]), np.array([1000.0, 1000.0, 1000.0])],
        )

        results = pump_system.evaluate_consumers(operational_setting=operational_settings)

        np.testing.assert_allclose(results[0].energy_usage, 1.683962, rtol=0.05)
        np.testing.assert_allclose(results[1].energy_usage, 1.703977, rtol=0.05)

    def test_consumer_system_pumps(self, pump_system):
        """Pump system integration test with realistic setup. To ensure correct calculations."""
        total_rate = np.asarray([1300, 13000])
        suction_pressure = np.asarray([1, 1])
        discharge_pressure = np.asarray([100, 100])
        fluid_density = np.asarray([1000, 1000])

        pump_system_operational_setting = PumpSystemOperationalSetting(
            rates=[total_rate / 2, total_rate / 2],
            suction_pressures=[suction_pressure, suction_pressure],
            discharge_pressures=[discharge_pressure, discharge_pressure],
            fluid_densities=[fluid_density, fluid_density],
        )
        operational_setting_result = pump_system.evaluate_system_operational_settings(
            operational_settings=[pump_system_operational_setting]
        )
        consumer_system_energy_usage = operational_setting_result[0].total_energy_usage

        # pump direct results, half the rate each
        density = np.asarray([fluid_density[0]])
        rate = np.asarray([total_rate[0]])
        ps = np.asarray([suction_pressure[0]])
        prd = np.asarray([discharge_pressure[0]])

        pump1_result = (
            pump_system.consumers[0]
            .facility_model.evaluate_rate_ps_pd_density(
                rate=rate,
                suction_pressures=ps,
                discharge_pressures=prd,
                fluid_density=density,
            )
            .energy_usage
        )
        pump2_result = (
            pump_system.consumers[1]
            .facility_model.evaluate_rate_ps_pd_density(
                rate=rate,
                suction_pressures=ps,
                discharge_pressures=prd,
                fluid_density=density,
            )
            .energy_usage
        )

        assert (pump1_result[0] + pump2_result[0]) == consumer_system_energy_usage[0]

    def test_pump_consumer_function_and_pump_system_consumer_function(self):
        # Single speed pump chart
        df = pd.DataFrame(
            [
                [277, 1061.7, 0.4759],
                [524, 1003.6, 0.6426],
                [666, 943.4, 0.6871],
                [832, 846.9, 0.7052],
                [834, 847.4, 0.7061],
                [927, 775.3, 0.6908],
            ],
            columns=["RATE", "HEAD", "EFFICIENCY"],
        )
        pump = PumpSingleSpeed(
            pump_chart=SingleSpeedChart(
                SingleSpeedChartDTO(
                    rate_actual_m3_hour=df["RATE"].tolist(),
                    polytropic_head_joule_per_kg=[x * 9.81 for x in df["HEAD"].tolist()],  # [m] to [J/kg]
                    efficiency_fraction=df["EFFICIENCY"].tolist(),
                    speed_rpm=1,
                )
            )
        )

        operational_settings_expressions = [
            PumpSystemOperationalSettingExpressions(
                rates=[Expression.setup_from_expression(6648)],
                suction_pressures=[Expression.setup_from_expression(1.0)],
                discharge_pressures=[Expression.setup_from_expression(107.30993)],
                fluid_densities=[Expression.setup_from_expression(1021)],
            )
        ]
        pump_system_consumer_function = PumpSystemConsumerFunction(
            consumer_components=[ConsumerSystemComponent(name="pump1", facility_model=pump)],
            operational_settings_expressions=operational_settings_expressions,
            condition_expression=None,
            power_loss_factor_expression=None,
        )

        variables_map = VariablesMap(
            variables={
                "SIM1;OIL_PROD_TOTAL": [25467.30664, 63761.23828, 145408.54688],
                "SIM1;OIL_PROD_RATE": [2829.70068, 7658.78613, 10205.91406],
            },
            time_vector=[
                datetime(1995, 10, 18, 0, 0),
                datetime(1995, 10, 27, 0, 0),
                datetime(1995, 11, 1, 0, 0),
                datetime(1995, 11, 9, 0, 0),
            ],
        )

        regularity = Expression.setup_from_expression(1).evaluate(
            variables=variables_map.variables, fill_length=variables_map.number_of_periods
        )
        result = pump_system_consumer_function.evaluate(
            expression_evaluator=variables_map,
            regularity=regularity.tolist(),
        )
        np.testing.assert_allclose(result.energy_usage, [1.719326, 1.719326, 1.719326], rtol=1e-5)

        pump_consumer_function = PumpConsumerFunction(
            pump_function=pump,
            rate_expression=Expression.setup_from_expression(6648.0),
            suction_pressure_expression=Expression.setup_from_expression(1.0),
            discharge_pressure_expression=Expression.setup_from_expression(107.30993),
            fluid_density_expression=Expression.setup_from_expression(1021),
        )
        power_loss_factor = 0.03
        pump_consumer_function_with_power_loss_factor = PumpConsumerFunction(
            pump_function=pump,
            rate_expression=Expression.setup_from_expression(6648.0),
            suction_pressure_expression=Expression.setup_from_expression(1.0),
            discharge_pressure_expression=Expression.setup_from_expression(107.30993),
            fluid_density_expression=Expression.setup_from_expression(1021),
            power_loss_factor_expression=Expression.setup_from_expression(str(power_loss_factor)),
        )

        result = pump_consumer_function.evaluate(expression_evaluator=variables_map, regularity=regularity.tolist())
        result_with_power_loss_factor = pump_consumer_function_with_power_loss_factor.evaluate(
            expression_evaluator=variables_map,
            regularity=regularity.tolist(),
        )
        np.testing.assert_allclose(result.energy_usage, [1.719326, 1.719326, 1.719326], rtol=1e-5)
        np.testing.assert_equal(
            result.energy_usage / (1 - power_loss_factor),
            result_with_power_loss_factor.energy_usage,
        )


class TestCompressorSystemConsumerFunction:
    def test_compressor_system_regularity(self, compressor_system_single, consumer_system_variables_map):
        """Regularity only affects the rate: rate_stream_day = rate_calendar_day / regularity,
        regularity is between 0 and 1 (fraction of "full time").
        """
        operational_settings_expressions_evaluated = compressor_system_single.get_operational_settings_from_expressions(
            expression_evaluator=consumer_system_variables_map,
            regularity=[1.0] * consumer_system_variables_map.number_of_periods,
        )

        operational_settings_expressions_evaluated_with_regularity = (
            compressor_system_single.get_operational_settings_from_expressions(
                expression_evaluator=consumer_system_variables_map,
                regularity=[0.9] * consumer_system_variables_map.number_of_periods,
            )
        )

        np.testing.assert_allclose(
            operational_settings_expressions_evaluated_with_regularity[0].rates,
            np.divide(operational_settings_expressions_evaluated[0].rates, 0.9),
        )

    def test_evaluate_evaluate_operational_setting_expressions(self, compressor_system_single):
        variables_map = VariablesMap(
            variables={
                "SIM1;OIL_PROD_TOTAL": [25467.30664, 63761.23828, 145408.54688],
                "SIM1;OIL_PROD_RATE": [2829.70068, 7658.78613, 10205.91406],
            },
            time_vector=[
                datetime(1995, 10, 18, 0, 0),
                datetime(1995, 10, 27, 0, 0),
                datetime(1995, 11, 1, 0, 0),
                datetime(1995, 11, 9, 0, 0),
            ],
        )
        result = compressor_system_single.evaluate_operational_setting_expressions(
            operational_setting_expressions=compressor_system_single.operational_settings_expressions[0],
            expression_evaluator=variables_map,
        )

        assert result.rates[0].tolist() == [1, 1, 1]
        assert result.suction_pressures[0].tolist() == [1, 1, 1]
        assert result.discharge_pressures[0].tolist() == [2, 2, 2]

    def test_evaluate_consumers(self, compressor_system_sampled):
        operational_settings = CompressorSystemOperationalSetting(
            rates=[np.array([2000000.0, 2000000.0, 2000000.0]), np.array([2000000.0, 2000000.0, 2000000.0])],
            suction_pressures=[np.array([10.0, 10.0, 10.0]), np.array([10.0, 10.0, 10.0])],
            discharge_pressures=[np.array([20.0, 20.0, 20.0]), np.array([20.0, 20.0, 20.0])],
            cross_overs=None,
        )

        results = compressor_system_sampled.evaluate_consumers(operational_setting=operational_settings)

        np.testing.assert_allclose(results[0].energy_usage, 146750, rtol=0.05)
        np.testing.assert_allclose(results[1].energy_usage, 146750, rtol=0.05)

    def test_consumer_system_consumer_function_evaluate(self, compressor_system_sampled_2):
        # Test with compressors
        dummy_suction_expression = Expression.setup_from_expression(10)
        dummy_discharge_expression = Expression.setup_from_expression(100)
        operational_setting1_expressions = CompressorSystemOperationalSettingExpressions(
            rates=[Expression.setup_from_expression("SIM1;GAS_PROD"), Expression.setup_from_expression(0)],
            suction_pressures=[dummy_suction_expression, dummy_suction_expression],
            discharge_pressures=[dummy_discharge_expression, dummy_discharge_expression],
        )
        operational_setting2_expressions = CompressorSystemOperationalSettingExpressions(
            rates=[
                Expression.setup_from_expression("SIM1;GAS_PROD {/} 2"),
                Expression.setup_from_expression("SIM1;GAS_PROD {/} 2"),
            ],
            suction_pressures=[dummy_suction_expression, dummy_suction_expression],
            discharge_pressures=[dummy_discharge_expression, dummy_discharge_expression],
        )
        operational_setting3_expressions = CompressorSystemOperationalSettingExpressions(
            rates=[
                Expression.setup_from_expression("SIM1;GAS_PROD {/} 2"),
                Expression.setup_from_expression("SIM1;GAS_PROD {/} 2"),
            ],
            suction_pressures=[dummy_suction_expression, dummy_suction_expression],
            discharge_pressures=[dummy_discharge_expression, dummy_discharge_expression],
        )
        consumer_system_function = CompressorSystemConsumerFunction(
            consumer_components=compressor_system_sampled_2.consumers,
            operational_settings_expressions=[
                operational_setting1_expressions,
                operational_setting2_expressions,
                operational_setting3_expressions,
            ],
            condition_expression=None,
            power_loss_factor_expression=None,
        )
        consumer_system_function_with_power_loss = CompressorSystemConsumerFunction(
            consumer_components=compressor_system_sampled_2.consumers,
            operational_settings_expressions=[
                operational_setting1_expressions,
                operational_setting2_expressions,
                operational_setting3_expressions,
            ],
            condition_expression=None,
            power_loss_factor_expression=Expression.setup_from_expression("SIM1;GAS_PROD {/} 10"),
        )

        gas_prod_values = [0.005, 1.5, 4, 4, 4, 4, 4, 4, 4, 4]
        variables_map = VariablesMap(
            variables={"SIM1;GAS_PROD": gas_prod_values},
            time_vector=[datetime(2000 + i, 1, 1) for i in range(11)],
        )
        result = consumer_system_function.evaluate(
            expression_evaluator=variables_map,
            regularity=[1.0] * variables_map.number_of_periods,
        )
        result_with_power_loss = consumer_system_function_with_power_loss.evaluate(
            expression_evaluator=variables_map,
            regularity=[1.0] * variables_map.number_of_periods,
        )
        np.testing.assert_equal(
            result_with_power_loss.energy_usage,
            result.energy_usage / (1 - np.array(gas_prod_values) / 10.0),
        )

        consumer_system_function_with_condition = CompressorSystemConsumerFunction(
            consumer_components=compressor_system_sampled_2.consumers,
            operational_settings_expressions=[
                operational_setting1_expressions,
                operational_setting2_expressions,
                operational_setting3_expressions,
            ],
            condition_expression=Expression.setup_from_expression("SIM1;GAS_PROD > 2"),
            power_loss_factor_expression=None,
        )

        result_with_condition = consumer_system_function_with_condition.evaluate(
            expression_evaluator=variables_map,
            regularity=[1.0] * variables_map.number_of_periods,
        )

        assert np.all(result_with_condition.condition == [0, 0, 1, 1, 1, 1, 1, 1, 1, 1])
        assert np.all(result_with_condition.energy_usage[0:2] == 0)

        # GAS_PROD=0.005: one compressor, midway between 1 and second entry - in the "jump" when the first compressor is turned on, operational setting should be 0
        # GAS_PROD=1.5 - midway between 11 and 12, should be 11.5 and operational setting should be 0
        # GAS_PROD=4 - to compressors on max capacity, using 12 each, thus 24 in total. Operational setting should be 1 (when two compressors are used)
        np.testing.assert_allclose(actual=result.energy_usage, desired=[5, 11.5, 24, 24, 24, 24, 24, 24, 24, 24])
        np.testing.assert_equal(actual=result.operational_setting_used, desired=[0, 0, 1, 1, 1, 1, 1, 1, 1, 1])
        # First operational setting. First consumer has nan for rate 4 above maximum, second consumer has only zeros as the rate is zero
        assert np.isnan(result.operational_settings_results[0][0].consumer_results[0].energy_usage[-1])
        np.testing.assert_equal(
            actual=np.asarray(result.operational_settings_results[0][0].consumer_results[1].energy_usage),
            desired=0.0,
        )
        # Second operational setting. Rate is split equally between both compressors and both end up at 12
        assert result.operational_settings_results[0][1].consumer_results[0].energy_usage[-1] == pytest.approx(12)
        assert result.operational_settings_results[0][1].consumer_results[1].energy_usage[-1] == pytest.approx(12)
