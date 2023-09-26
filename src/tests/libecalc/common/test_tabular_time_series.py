from datetime import datetime
from typing import List

import pytest
from libecalc.common.stream import Stage, Stream
from libecalc.common.tabular_time_series import TabularTimeSeriesUtils
from libecalc.common.units import Unit
from libecalc.common.utils.rates import TimeSeriesFloat, TimeSeriesRate
from libecalc.dto.types import RateType
from pydantic import BaseModel


class MergeableObject(BaseModel):
    string_test: str
    int_test: int
    float_test: float
    list_of_float_test: List[float]
    time_series_float: TimeSeriesFloat
    time_series_rate: TimeSeriesRate
    time_series_float_list_test: List[TimeSeriesFloat]
    time_series_rate_list_test: List[TimeSeriesRate]
    stage_list: List[Stage]


class TestMerge:
    def test_valid_merge(self):
        first_timesteps = [datetime(2020, 1, 1), datetime(2022, 1, 1)]
        first = MergeableObject(
            string_test="1",
            int_test=15,
            float_test=1.0,
            list_of_float_test=[11, 12, 13, 14, 15],
            time_series_rate=TimeSeriesRate(
                timesteps=first_timesteps,
                values=[11, 12],
                unit=Unit.NORWEGIAN_KRONER,
                regularity=[11, 12],
                rate_type=RateType.CALENDAR_DAY,
            ),
            time_series_float=TimeSeriesFloat(
                timesteps=first_timesteps,
                values=[11, 12],
                unit=Unit.NORWEGIAN_KRONER,
            ),
            time_series_float_list_test=[
                TimeSeriesFloat(
                    timesteps=first_timesteps,
                    values=[111, 112],
                    unit=Unit.NORWEGIAN_KRONER,
                ),
                TimeSeriesFloat(
                    timesteps=first_timesteps,
                    values=[-121, -122],
                    unit=Unit.NORWEGIAN_KRONER,
                ),
            ],
            time_series_rate_list_test=[
                TimeSeriesRate(
                    timesteps=first_timesteps,
                    values=[111, 112],
                    unit=Unit.NORWEGIAN_KRONER,
                    regularity=[111, 112],
                    rate_type=RateType.CALENDAR_DAY,
                ),
                TimeSeriesRate(
                    timesteps=first_timesteps,
                    values=[-121, -122],
                    unit=Unit.NORWEGIAN_KRONER,
                    regularity=[121, 122],
                    rate_type=RateType.CALENDAR_DAY,
                ),
            ],
            stage_list=[
                Stage(
                    name="inlet",
                    stream=Stream(
                        rate=TimeSeriesRate(
                            timesteps=first_timesteps,
                            values=[-111, -112],
                            unit=Unit.NORWEGIAN_KRONER,
                            regularity=[111, 112],
                            rate_type=RateType.CALENDAR_DAY,
                        ),
                        pressure=TimeSeriesFloat(
                            timesteps=first_timesteps,
                            values=[-111, -112],
                            unit=Unit.BARA,
                        ),
                    ),
                ),
                Stage(
                    name="outlet",
                    stream=Stream(
                        rate=TimeSeriesRate(
                            timesteps=first_timesteps,
                            values=[-121, -122],
                            unit=Unit.NORWEGIAN_KRONER,
                            regularity=[121, 122],
                            rate_type=RateType.CALENDAR_DAY,
                        ),
                        pressure=TimeSeriesFloat(
                            timesteps=first_timesteps,
                            values=[-121, -122],
                            unit=Unit.BARA,
                        ),
                    ),
                ),
            ],
        )

        second_timesteps = [datetime(2021, 1, 1), datetime(2023, 1, 1)]
        second = MergeableObject(
            string_test="2",
            int_test=25,
            float_test=2.0,
            list_of_float_test=[21, 22, 23, 24, 25],
            time_series_float=TimeSeriesFloat(
                timesteps=second_timesteps,
                values=[21, 22],
                unit=Unit.NORWEGIAN_KRONER,
            ),
            time_series_rate=TimeSeriesRate(
                timesteps=second_timesteps,
                values=[21, 22],
                unit=Unit.NORWEGIAN_KRONER,
                regularity=[21, 22],
                rate_type=RateType.CALENDAR_DAY,
            ),
            time_series_float_list_test=[
                TimeSeriesFloat(
                    timesteps=second_timesteps,
                    values=[211, 212],
                    unit=Unit.NORWEGIAN_KRONER,
                ),
                TimeSeriesFloat(
                    timesteps=second_timesteps,
                    values=[-221, -222],
                    unit=Unit.NORWEGIAN_KRONER,
                ),
            ],
            time_series_rate_list_test=[
                TimeSeriesRate(
                    timesteps=second_timesteps,
                    values=[211, 212],
                    unit=Unit.NORWEGIAN_KRONER,
                    regularity=[211, 212],
                    rate_type=RateType.CALENDAR_DAY,
                ),
                TimeSeriesRate(
                    timesteps=second_timesteps,
                    values=[-221, -222],
                    unit=Unit.NORWEGIAN_KRONER,
                    regularity=[221, 222],
                    rate_type=RateType.CALENDAR_DAY,
                ),
            ],
            stage_list=[
                Stage(
                    name="inlet",
                    stream=Stream(
                        rate=TimeSeriesRate(
                            timesteps=second_timesteps,
                            values=[-211, -212],
                            unit=Unit.NORWEGIAN_KRONER,
                            regularity=[211, 212],
                            rate_type=RateType.CALENDAR_DAY,
                        ),
                        pressure=TimeSeriesFloat(
                            timesteps=second_timesteps,
                            values=[-211, -212],
                            unit=Unit.BARA,
                        ),
                    ),
                ),
                Stage(
                    name="outlet",
                    stream=Stream(
                        rate=TimeSeriesRate(
                            timesteps=second_timesteps,
                            values=[-221, -222],
                            unit=Unit.NORWEGIAN_KRONER,
                            regularity=[221, 222],
                            rate_type=RateType.CALENDAR_DAY,
                        ),
                        pressure=TimeSeriesFloat(
                            timesteps=second_timesteps,
                            values=[-221, -222],
                            unit=Unit.BARA,
                        ),
                    ),
                ),
            ],
        )

        merged = TabularTimeSeriesUtils.merge(first, second)

        expected_timesteps = [datetime(2020, 1, 1), datetime(2021, 1, 1), datetime(2022, 1, 1), datetime(2023, 1, 1)]

        assert (
            merged.dict()
            == MergeableObject(
                string_test="1",
                int_test=15,
                float_test=1.0,
                list_of_float_test=[11, 12, 13, 14, 15],
                time_series_float=TimeSeriesFloat(
                    timesteps=expected_timesteps,
                    values=[11, 21, 12, 22],
                    unit=Unit.NORWEGIAN_KRONER,
                ),
                time_series_rate=TimeSeriesRate(
                    timesteps=expected_timesteps,
                    values=[11, 21, 12, 22],
                    unit=Unit.NORWEGIAN_KRONER,
                    regularity=[11, 21, 12, 22],
                    rate_type=RateType.CALENDAR_DAY,
                ),
                time_series_float_list_test=[
                    TimeSeriesFloat(
                        timesteps=expected_timesteps,
                        values=[111, 211, 112, 212],
                        unit=Unit.NORWEGIAN_KRONER,
                    ),
                    TimeSeriesFloat(
                        timesteps=expected_timesteps,
                        values=[-121, -221, -122, -222],
                        unit=Unit.NORWEGIAN_KRONER,
                    ),
                ],
                time_series_rate_list_test=[
                    TimeSeriesRate(
                        timesteps=expected_timesteps,
                        values=[111, 211, 112, 212],
                        unit=Unit.NORWEGIAN_KRONER,
                        regularity=[111, 211, 112, 212],
                        rate_type=RateType.CALENDAR_DAY,
                    ),
                    TimeSeriesRate(
                        timesteps=expected_timesteps,
                        values=[-121, -221, -122, -222],
                        unit=Unit.NORWEGIAN_KRONER,
                        regularity=[121, 221, 122, 222],
                        rate_type=RateType.CALENDAR_DAY,
                    ),
                ],
                stage_list=[
                    Stage(
                        name="inlet",
                        stream=Stream(
                            rate=TimeSeriesRate(
                                timesteps=expected_timesteps,
                                values=[-111, -211, -112, -212],
                                unit=Unit.NORWEGIAN_KRONER,
                                regularity=[111, 211, 112, 212],
                                rate_type=RateType.CALENDAR_DAY,
                            ),
                            pressure=TimeSeriesFloat(
                                timesteps=expected_timesteps,
                                values=[-111, -211, -112, -212],
                                unit=Unit.BARA,
                            ),
                        ),
                    ),
                    Stage(
                        name="outlet",
                        stream=Stream(
                            rate=TimeSeriesRate(
                                timesteps=expected_timesteps,
                                values=[-121, -221, -122, -222],
                                unit=Unit.NORWEGIAN_KRONER,
                                regularity=[121, 221, 122, 222],
                                rate_type=RateType.CALENDAR_DAY,
                            ),
                            pressure=TimeSeriesFloat(
                                timesteps=expected_timesteps,
                                values=[-121, -221, -122, -222],
                                unit=Unit.BARA,
                            ),
                        ),
                    ),
                ],
            ).dict()
        )

    def test_invalid_types(self):
        class First(BaseModel):
            something: TimeSeriesFloat

        first = First(
            something=TimeSeriesFloat(
                timesteps=[datetime(2022, 1, 1)],
                values=[1],
                unit=Unit.NONE,
            )
        )

        class Other(BaseModel):
            something: List[int]

        other = Other(something=[1, 2])

        with pytest.raises(ValueError) as exc_info:
            TabularTimeSeriesUtils.merge(first, other)

        assert str(exc_info.value) == "Can not merge objects of differing types."
