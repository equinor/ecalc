from datetime import datetime

import pytest

from libecalc.domain.infrastructure.energy_components.legacy_consumer.system.operational_setting import (
    ConsumerSystemOperationalSettingExpressions,
)


@pytest.fixture
def consumer_system_variables_map(expression_evaluator_factory):
    time_vector = [
        datetime(2020, 1, 1),
        datetime(2021, 1, 1),
        datetime(2022, 1, 1),
    ]
    return expression_evaluator_factory.from_time_vector(time_vector)


@pytest.fixture
def operational_settings_factory(
    time_series_flow_rate_factory, time_series_pressure_factory, time_series_density_factory
):
    def create_operational_settings_from_lists(
        rates: list[list[float]],
        suction_pressures: list[float],
        discharge_pressures: list[float],
        cross_overs: list[int],
        fluid_densities: list[float],
    ):
        length = len(rates[0])
        return ConsumerSystemOperationalSettingExpressions(
            rates=[time_series_flow_rate_factory(values=rate) for rate in rates],
            fluid_densities=[time_series_density_factory(values=[density] * length) for density in fluid_densities],
            suction_pressures=[
                time_series_pressure_factory(values=[suction_pressure] * length)
                for suction_pressure in suction_pressures
            ],
            discharge_pressures=[
                time_series_pressure_factory(values=[discharge_pressure] * length)
                for discharge_pressure in discharge_pressures
            ],
            cross_overs=cross_overs,
        )

    return create_operational_settings_from_lists


class TestConsumerSystemConsumerFunction:
    @pytest.mark.parametrize(
        "rates, max_rates, expected_crossover_used, expected_is_valid",
        [
            ([[100], [100]], [100, 100], [False], [True, True]),
            ([[101], [100]], [100, 100], [True], [True, False]),
            ([[100], [101]], [100, 101], [False], [True, True]),
        ],
    )
    def test_crossovers(
        self,
        system_component_factory,
        operational_settings_factory,
        system_factory,
        rates,
        max_rates,
        expected_crossover_used,
        expected_is_valid,
    ):
        operational_setting = operational_settings_factory(
            rates=rates,
            suction_pressures=[1, 1],
            discharge_pressures=[100, 100],
            cross_overs=[2, 0],
            fluid_densities=[1000, 1000],
        )

        system_components = [
            system_component_factory(
                name=str(i),
                max_rate=[max_rate],
            )
            for i, max_rate in enumerate(max_rates)
        ]

        system = system_factory(system_components=system_components, operational_settings=[operational_setting])

        result = system.evaluate()

        assert result.cross_over_used.tolist() == expected_crossover_used

        for consumer_result, expected_consumer_is_valid in zip(result.consumer_results, expected_is_valid):
            assert consumer_result.result.get_energy_result().is_valid[0] == expected_consumer_is_valid

    @pytest.mark.parametrize(
        "rates, max_rate, expected_operational_settings_used, expected_is_valid",
        [
            ([[101], [99]], 100, [1], True),  # Second used, valid
            ([[99], [101]], 100, [0], True),  # First used, valid
            ([[101], [101]], 100, [1], False),  # Invalid, last used
        ],
    )
    def test_operational_settings_used(
        self,
        system_component_factory,
        operational_settings_factory,
        system_factory,
        rates,
        max_rate,
        expected_operational_settings_used,
        expected_is_valid,
    ):
        operational_settings = [
            operational_settings_factory(
                rates=[rate],
                suction_pressures=[1],
                discharge_pressures=[100],
                cross_overs=[0],
                fluid_densities=[1000],
            )
            for rate in rates
        ]

        system_components = [
            system_component_factory(
                name="only_one",
                max_rate=[max_rate],
            )
        ]

        system = system_factory(system_components=system_components, operational_settings=operational_settings)

        result = system.evaluate()

        assert result.operational_setting_used.tolist() == expected_operational_settings_used
        assert result.is_valid[0] == expected_is_valid
