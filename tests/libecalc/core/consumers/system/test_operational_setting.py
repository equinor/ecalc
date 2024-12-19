from unittest.mock import patch

import numpy as np
import pytest

from libecalc.common.errors.exceptions import EcalcError
from libecalc.domain.infrastructure.energy_components.legacy_consumer.system.operational_setting import (
    ConsumerSystemOperationalSetting,
    ConsumerSystemOperationalSettingExpressions,
)
from libecalc.expression import Expression


def test_consumer_system_operational_settings_expression():
    number_of_consumers = 3

    operational_settings_expression = ConsumerSystemOperationalSettingExpressions(
        rates=[Expression.setup_from_expression(1)] * number_of_consumers,
        suction_pressures=[Expression.setup_from_expression(1)] * number_of_consumers,
        discharge_pressures=[Expression.setup_from_expression(2)] * number_of_consumers,
    )

    assert operational_settings_expression.number_of_consumers == number_of_consumers


class TestConsumerSystemOperationalSetting:
    def test_operational_setting(self):
        operational_settings = ConsumerSystemOperationalSetting(
            rates=[np.array([1, 2, 3])],
            suction_pressures=[np.array([1, 2, 3])],
            discharge_pressures=[np.array([1, 2, 3])],
        )

        assert operational_settings.rates[0].tolist() == [1, 2, 3]
        assert operational_settings.suction_pressures[0].tolist() == [1, 2, 3]
        assert operational_settings.discharge_pressures[0].tolist() == [1, 2, 3]

    def test_mismatching_settings_length(self):
        with pytest.raises(EcalcError) as e:
            ConsumerSystemOperationalSetting(
                rates=[np.array([1])],
                suction_pressures=[np.array([1]), np.array([1])],
                discharge_pressures=[np.array([1]), np.array([1]), np.array([1])],
            )

        assert (
            "All attributes in a consumer system operational setting"
            " must have the same number of elements(corresponding to the number of consumers)." in str(e.value)
        )

    def test_convert_rates_to_stream_day(self):
        """Using regularity 0.5 the rate will double. Everything else stays the same."""
        operational_setting = ConsumerSystemOperationalSetting(
            rates=[np.array([1, 2, 3]).astype(float)],
            suction_pressures=[np.array([1, 2, 3]).astype(float)],
            discharge_pressures=[np.array([1, 2, 3]).astype(float)],
        )

        result = operational_setting.convert_rates_to_stream_day(regularity=0.5)
        assert result.rates[0].tolist() == [2, 4, 6]
        assert result.suction_pressures[0].tolist() == [1, 2, 3]
        assert result.discharge_pressures[0].tolist() == [1, 2, 3]

    def test_add_crossed_over_rates(self):
        """Return a clone of the CompressorSystemOperationalSetting and set the attribute for rate after crossover."""
        operational_setting = ConsumerSystemOperationalSetting(
            rates=[np.array([1, 2, 3])],
            suction_pressures=[np.array([1, 2, 3])],
            discharge_pressures=[np.array([1, 2, 3])],
        )

        result = operational_setting.set_rates_after_cross_over(rates_after_cross_over=[np.array([0.5, 1.0, 1.5])])
        assert result.rates[0].tolist() == [0.5, 1.0, 1.5]
