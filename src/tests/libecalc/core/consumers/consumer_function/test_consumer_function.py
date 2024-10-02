from datetime import datetime

import numpy as np

from libecalc.common.time_utils import Periods
from libecalc.common.units import Unit
from libecalc.core.consumers.legacy_consumer.consumer_function import (
    ConsumerFunctionResult,
)
from libecalc.core.consumers.legacy_consumer.consumer_function.types import (
    ConsumerFunctionType,
)
from libecalc.core.models.results import EnergyFunctionGenericResult


def test_consumer_function_result_append():
    result = ConsumerFunctionResult(
        typ=ConsumerFunctionType.SINGLE,
        periods=Periods.create_periods(
            times=[
                datetime(2018, 1, 1, 0, 0),
                datetime(2019, 1, 1, 0, 0),
            ],
            include_before=False,
            include_after=False,
        ),
        is_valid=~np.isnan(np.array([1.0])),
        energy_usage=np.array([1.0]),
        energy_usage_before_power_loss_factor=np.array([1.0]),
        condition=None,
        power_loss_factor=None,
        energy_function_result=EnergyFunctionGenericResult(
            energy_usage=[1.0],
            energy_usage_unit=Unit.MEGA_WATT,
            power=[1.0],
            power_unit=Unit.MEGA_WATT,
        ),
    )

    other_result = ConsumerFunctionResult(
        typ=ConsumerFunctionType.SINGLE,
        periods=Periods.create_periods(
            times=[
                datetime(2019, 1, 1, 0, 0),
                datetime(2020, 1, 1, 0, 0),
            ],
            include_before=False,
            include_after=False,
        ),
        is_valid=~np.isnan(np.array([2.0])),
        energy_usage=np.array([2.0]),
        energy_usage_before_power_loss_factor=np.array([2.0]),
        condition=None,
        power_loss_factor=None,
        energy_function_result=EnergyFunctionGenericResult(
            energy_usage=[2.0],
            energy_usage_unit=Unit.MEGA_WATT,
            power=[2.0],
            power_unit=Unit.MEGA_WATT,
        ),
    )

    updated_result = result.extend(other_result)

    assert updated_result.typ == ConsumerFunctionType.SINGLE
    np.testing.assert_equal(
        updated_result.periods,
        Periods.create_periods(
            times=[
                datetime(2018, 1, 1, 0, 0),
                datetime(2019, 1, 1, 0, 0),
                datetime(2020, 1, 1, 0, 0),
            ],
            include_after=False,
            include_before=False,
        ),
    )
    np.testing.assert_equal(updated_result.energy_usage, np.array([1.0, 2.0]))
    np.testing.assert_equal(updated_result.energy_usage_before_power_loss_factor, np.array([1.0, 2.0]))
    assert updated_result.condition is None
    assert updated_result.power_loss_factor is None
    np.testing.assert_equal(updated_result.energy_function_result.energy_usage, np.array([1.0, 2.0]))
    assert updated_result.energy_function_result.energy_usage_unit == Unit.MEGA_WATT
    np.testing.assert_equal(updated_result.energy_function_result.power, np.array([1.0, 2.0]))
    assert updated_result.energy_function_result.power_unit == Unit.MEGA_WATT
