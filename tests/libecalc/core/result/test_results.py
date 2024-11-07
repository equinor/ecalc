from datetime import datetime

from libecalc.common.time_utils import Periods
from libecalc.common.units import Unit
from libecalc.common.utils.rates import (
    TimeSeriesBoolean,
    TimeSeriesStreamDayRate,
)
from libecalc.core.result import CompressorResult


class TestMerge:
    def test_merge_compressor_result(self):
        periods = Periods.create_periods(
            times=[
                datetime(2019, 1, 1),
                datetime(2020, 1, 1),
                datetime(2021, 1, 1),
                datetime(2022, 1, 1),
                datetime(2023, 1, 1),
            ],
            include_after=False,
            include_before=False,
        )
        compressor_result = CompressorResult(
            periods=periods,
            energy_usage=TimeSeriesStreamDayRate(
                periods=periods,
                values=[1, 2, 3, 4],
                unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
            ),
            power=TimeSeriesStreamDayRate(
                periods=periods,
                values=[1, 2, 3, 4],
                unit=Unit.MEGA_WATT,
            ),
            is_valid=TimeSeriesBoolean(
                periods=periods,
                values=[True, True, True, True],
                unit=Unit.NONE,
            ),
            recirculation_loss=TimeSeriesStreamDayRate(
                periods=periods,
                values=[0.1, 0.2, 0.3, 0.4],
                unit=Unit.MEGA_WATT,
            ),
            rate_exceeds_maximum=TimeSeriesBoolean(
                periods=periods,
                values=[False, False, False, False],
                unit=Unit.NONE,
            ),
            id="My test component",
        )

        compressor_result_subset_1 = compressor_result.get_subset([0, 1])

        compressor_result_subset_2 = compressor_result.get_subset([2, 3])

        assert (
            compressor_result_subset_1.merge(compressor_result_subset_2).model_dump() == compressor_result.model_dump()
        )
