from math import nan

import numpy as np
import pandas as pd

from libecalc.core.models.compressor.sampled.compressor_model_sampled_1d import (
    CompressorModelSampled1D,
)
from libecalc.core.models.compressor.sampled.constants import (
    PD_NAME,
    PS_NAME,
    RATE_NAME,
)


def _create_sampled_data(
    sampled_data: list[list[int]],
    x_column_name: str,
    function_value_header: str = "FUEL",
) -> pd.DataFrame:
    sampled_data = pd.DataFrame(sampled_data)
    sampled_data.columns = [x_column_name, function_value_header]
    return sampled_data


def _run_compressor_model_sampled_1d(
    sampled_data,
    x_column_name,
    test_data,
    function_value_header="FUEL",
):
    sampled_data = _create_sampled_data(sampled_data, x_column_name, function_value_header)
    compressor_model = CompressorModelSampled1D(sampled_data=sampled_data, function_header=function_value_header)
    if x_column_name == RATE_NAME:
        return compressor_model.evaluate(rate=test_data)
    elif x_column_name == PS_NAME:
        return compressor_model.evaluate(suction_pressure=test_data)
    elif x_column_name == PD_NAME:
        return compressor_model.evaluate(discharge_pressure=test_data)


def test_rate_ordered():
    y = _run_compressor_model_sampled_1d(
        sampled_data=[[2, 2], [3, 3], [4, 4]],
        x_column_name=RATE_NAME,
        test_data=[1, 2, 3, 4, 5],
    )
    expected = [2, 2, 3, 4, nan]
    np.testing.assert_array_equal(y, expected)


def test_rate_unordered():
    y = _run_compressor_model_sampled_1d(
        sampled_data=[[3, 3], [2, 2], [4, 4]],
        x_column_name=RATE_NAME,
        test_data=[1, 2, 3, 4, 5],
    )
    expected = [2, 2, 3, 4, nan]
    np.testing.assert_array_equal(y, expected)


def test_rate_with_power():
    y = _run_compressor_model_sampled_1d(
        sampled_data=[[3, 3], [2, 2], [4, 4]],
        x_column_name=RATE_NAME,
        test_data=[1, 2, 3, 4, 5],
        function_value_header="POWER",
    )
    expected = [2, 2, 3, 4, nan]
    np.testing.assert_array_equal(y, expected)


def test_pd():
    y = _run_compressor_model_sampled_1d(
        sampled_data=[[3, 3], [2, 2], [4, 4]],
        x_column_name=PD_NAME,
        test_data=[1, 2, 3, 4, 5],
    )
    expected = [2, 2, 3, 4, nan]
    np.testing.assert_array_equal(y, expected)


def test_ps():
    y = _run_compressor_model_sampled_1d(
        sampled_data=[[3, 3], [2, 4], [4, 2]],
        x_column_name=PS_NAME,
        test_data=[1, 2, 3, 4, 5],
    )
    expected = [nan, 4, 3, 2, 2]
    np.testing.assert_array_equal(y, expected)


def test_max_rate_rate():
    sampled_data = _create_sampled_data(
        sampled_data=[[3, 3], [2, 4], [4, 2]],
        x_column_name=RATE_NAME,
    )
    compressor_model = CompressorModelSampled1D(
        sampled_data=sampled_data,
        function_header="FUEL",
    )
    assert compressor_model.get_max_rate() == 4


def test_max_rate_ps():
    sampled_data = _create_sampled_data(
        sampled_data=[[3, 3], [2, 2], [4, 4]],
        x_column_name=PS_NAME,
    )
    compressor_model = CompressorModelSampled1D(
        sampled_data=sampled_data,
        function_header="FUEL",
    )
    assert compressor_model.get_max_rate() is None


def test_max_rate_pd():
    sampled_data = _create_sampled_data(
        sampled_data=[[3, 3], [2, 2], [4, 4]],
        x_column_name=PD_NAME,
    )
    compressor_model = CompressorModelSampled1D(
        sampled_data=sampled_data,
        function_header="FUEL",
    )
    assert compressor_model.get_max_rate() is None
