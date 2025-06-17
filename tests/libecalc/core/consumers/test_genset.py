from datetime import datetime

import numpy as np
import pytest

from libecalc.common.units import Unit
from libecalc.common.utils.rates import (
    TimeSeriesBoolean,
    TimeSeriesFloat,
    TimeSeriesStreamDayRate,
)


@pytest.fixture
def time_vector() -> list[datetime]:
    return [
        datetime(2020, 1, 1),
        datetime(2021, 1, 1),
        datetime(2022, 1, 1),
        datetime(2023, 1, 1),
        datetime(2024, 1, 1),
        datetime(2025, 1, 1),
        datetime(2026, 1, 1),
    ]


def test_genset_with_elconsumer_nan_results(genset_2mw_dto, fuel_dto, expression_evaluator_factory, time_vector):
    """Testing what happens when the el-consumers has nan-values in power. -> Genset should not do anything."""
    variables = expression_evaluator_factory.from_time_vector(time_vector=time_vector)
    genset_2mw_dto = genset_2mw_dto(variables)

    power_requirement = TimeSeriesFloat(
        periods=variables.get_periods(),
        values=[np.nan, np.nan, 0.5, 0.5, np.nan, np.nan],
        unit=Unit.MEGA_WATT,
    )

    results = genset_2mw_dto.evaluate_process_model(
        power_requirement=power_requirement,
    )

    # The Genset is not supposed to handle NaN-values from the el-consumers.
    np.testing.assert_equal(results.power.values, [np.nan, np.nan, 0.5, 0.5, np.nan, np.nan])
    assert results.power.unit == Unit.MEGA_WATT
    assert results.power.periods == variables.periods

    # The resulting fuel rate will be zero and the result is invalid for the NaN periods.
    assert results.energy_usage == TimeSeriesStreamDayRate(
        periods=variables.periods,
        values=[0, 0, 0.6, 0.6, 0.0, 0.0],
        unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
    )
    assert results.is_valid == TimeSeriesBoolean(
        periods=variables.periods,
        values=[False, False, True, True, False, False],
        unit=Unit.NONE,
    )


def test_genset_outside_capacity(genset_2mw_dto, fuel_dto, expression_evaluator_factory, time_vector):
    """Testing what happens when the power rate is outside of genset capacity. -> Genset will limit to max capacity"""
    variables = expression_evaluator_factory.from_time_vector(time_vector=time_vector)
    genset_2mw_dto = genset_2mw_dto(variables)

    results = genset_2mw_dto.evaluate_process_model(
        power_requirement=TimeSeriesFloat(
            values=[1, 1, 3, 4, 5, 6],
            periods=variables.get_periods(),
            unit=Unit.MEGA_WATT,
        ),
    )

    # The genset will still report power rate
    assert results.power.periods == variables.periods
    assert results.power.values == [1, 1, 3, 4, 5, 6]
    assert results.power.unit == Unit.MEGA_WATT

    assert results.energy_usage.periods == variables.periods
    assert results.energy_usage.values == [1, 1, 2, 2, 2, 2]
    assert results.energy_usage.unit == Unit.STANDARD_CUBIC_METER_PER_DAY

    assert results.is_valid.periods == variables.periods
    assert results.is_valid.values == [True, True, False, False, False, False]


def test_genset_late_startup(
    genset_1000mw_late_startup_dto, fuel_dto, energy_model_from_dto_factory, expression_evaluator_factory, time_vector
):
    variables = expression_evaluator_factory.from_time_vector(time_vector=time_vector)
    genset_1000mw_late_startup_dto = genset_1000mw_late_startup_dto(variables)
    power_requirement = TimeSeriesFloat(
        values=[1.0, 2.0, 10.0, 0.0, 0.0, 0.0], periods=variables.get_periods(), unit=Unit.MEGA_WATT
    )
    generator_set_result = genset_1000mw_late_startup_dto.evaluate_process_model(power_requirement=power_requirement)

    assert generator_set_result.power == TimeSeriesStreamDayRate(
        periods=variables.periods,
        values=[1.0, 2.0, 10.0, 0.0, 0.0, 0.0],
        unit=Unit.MEGA_WATT,
    )

    # Note that the genset is not able to deliver the power rate demanded by the el-consumer(s) for the two
    # first time-steps before the genset is activated in 2022.
    assert generator_set_result.energy_usage == TimeSeriesStreamDayRate(
        periods=variables.periods,
        values=[0.0, 0.0, 10.0, 0.0, 0.0, 0.0],
        unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
    )
    assert generator_set_result.is_valid == TimeSeriesBoolean(
        periods=variables.periods,
        values=[False, False, True, True, True, True],
        unit=Unit.NONE,
    )
