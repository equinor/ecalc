from datetime import datetime

import numpy as np
import pandas as pd
import pytest
from libecalc.common.time_utils import Frequency

START_DATE = datetime(2020, 1, 1)
END_DATE = datetime(2022, 1, 1)


@pytest.fixture
def ds_time_series_daily() -> pd.Series:
    """Single time series."""
    freq = Frequency.DAY
    idx = pd.date_range(start=START_DATE, end=END_DATE, freq=freq.value)
    data = np.array(range(len(idx)))
    return pd.Series(data=data, index=idx, name="ts1")


@pytest.fixture
def ds_time_series_monthly() -> pd.Series:
    """Single time series."""
    freq = Frequency.MONTH
    idx = pd.date_range(start=START_DATE, end=END_DATE, freq=freq.value)
    data = np.array(range(len(idx)))
    return pd.Series(data=data, index=idx, name="ts1")


@pytest.fixture
def ds_time_series_yearly() -> pd.Series:
    """Single time series."""
    freq = Frequency.YEAR
    idx = pd.date_range(start=START_DATE, end=END_DATE, freq=freq.value)
    data = np.array(range(len(idx)))
    return pd.Series(data=data, index=idx, name="ts1")


def test_frequency(ds_time_series_daily, ds_time_series_monthly, ds_time_series_yearly):
    """Note that this is only valid as long as the START_DATE and END_DATE corresponds to a valid subset of the freq.
    I.e.
        Daily freq can have any START_DATE and END_DATE
        Month start freq needs to have START_DATE at 1. of a month and the same with END_DATE.
        Year start freq needs to have START_dATE at Jan 1. of a year, and the same with END_DATE.
    """
    assert START_DATE in ds_time_series_daily.index
    assert END_DATE in ds_time_series_daily.index
    assert START_DATE in ds_time_series_monthly.index
    assert END_DATE in ds_time_series_monthly.index
    assert START_DATE in ds_time_series_yearly.index
    assert END_DATE in ds_time_series_yearly.index


def test_frequency_to_string():
    # Todo: consider converting to ISO 8601 YYYY-MM-DD, YYYY-MM and YYYY
    assert Frequency.DAY.formatstring() == "%d/%m/%Y"
    assert Frequency.MONTH.formatstring() == "%m/%Y"
    assert Frequency.YEAR.formatstring() == "%Y"
