from datetime import datetime

from libecalc.common.units import Unit
from libecalc.common.utils.rates import (
    TimeSeriesBoolean,
    TimeSeriesFloat,
    TimeSeriesStreamDayRate,
)
from libecalc.core.result import CompressorResult


class TestMerge:
    def test_merge_compressor_result(self):
        timesteps = [
            datetime(2019, 1, 1),
            datetime(2020, 1, 1),
            datetime(2021, 1, 1),
            datetime(2022, 1, 1),
        ]
        compressor_result = CompressorResult(
            timesteps=timesteps,
            energy_usage=TimeSeriesStreamDayRate(
                timesteps=timesteps,
                values=[1, 2, 3, 4],
                unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
            ),
            power=TimeSeriesStreamDayRate(
                timesteps=timesteps,
                values=[1, 2, 3, 4],
                unit=Unit.MEGA_WATT,
            ),
            is_valid=TimeSeriesBoolean(
                timesteps=timesteps,
                values=[True, True, True, True],
                unit=Unit.NONE,
            ),
            recirculation_loss=TimeSeriesStreamDayRate(
                timesteps=timesteps,
                values=[0.1, 0.2, 0.3, 0.4],
                unit=Unit.MEGA_WATT,
            ),
            rate_exceeds_maximum=TimeSeriesBoolean(
                timesteps=timesteps,
                values=[False, False, False, False],
                unit=Unit.NONE,
            ),
            outlet_pressure_before_choking=TimeSeriesFloat(
                timesteps=timesteps,
                values=[150, 151, 152, 153],
                unit=Unit.BARA,
            ),
            id="My test component",
        )

        compressor_result_subset_1 = compressor_result.get_subset([0, 2])

        compressor_result_subset_2 = compressor_result.get_subset([1, 3])

        assert (
            compressor_result_subset_1.merge(compressor_result_subset_2).model_dump() == compressor_result.model_dump()
        )
