import csv
import json
import io
from datetime import datetime

import pytest

from ecalc_cli.types import DateFormat
from libecalc.common.datetime.utils import DateTimeFormats
from libecalc.common.time_utils import Frequency, Periods, Period
from libecalc.common.units import Unit
from libecalc.common.utils.rates import TimeSeriesRate, RateType
from libecalc.domain.emission.emission_intensity import (
    calculate_emission_intensity,
    EmissionIntensityResults,
    emission_intensity_to_csv,
)
from libecalc.domain.regularity import Regularity
from libecalc.presentation.json_result.result import EmissionResult


boe_factor = 6.29


@pytest.fixture
def simple_data(expression_evaluator_factory):
    # 3 periods, 1 unit each
    periods = Periods(
        [
            Period(start=datetime(2020, 1, 1), end=datetime(2020, 2, 1)),
            Period(start=datetime(2020, 2, 1), end=datetime(2020, 3, 1)),
            Period(start=datetime(2020, 3, 1), end=datetime(2020, 4, 1)),
        ]
    )

    expression_evaluator = expression_evaluator_factory.from_periods(
        variables={},
        periods=periods.periods,
    )
    regularity = Regularity(
        expression_input=1,
        expression_evaluator=expression_evaluator,
        target_period=expression_evaluator.get_period(),
    )

    # Hydrocarbon export: 1, 2, 3 (cumulative: 1, 3, 6)
    hc_export = TimeSeriesRate(
        periods=periods,
        values=[1, 2, 3],
        unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
        rate_type=RateType.STREAM_DAY,
        regularity=regularity.time_series.values,
    )

    # CO2 emission: 2, 4, 6 (cumulative: 2, 6, 12)
    co2_emission_rate = TimeSeriesRate(
        periods=periods,
        values=[2, 4, 6],
        unit=Unit.KILO_PER_DAY,
        rate_type=RateType.STREAM_DAY,
        regularity=regularity.time_series.values,
    )

    co2_emission_cumulative = co2_emission_rate.to_volumes().cumulative()

    co2_emission = EmissionResult(
        name="co2",
        periods=periods,
        rate=co2_emission_rate,
        cumulative=co2_emission_cumulative,
    )
    return hc_export, {"co2": co2_emission}


def test_correct_intensity(simple_data):
    """Test that emission intensity is calculated correctly for simple input data."""
    hc_export, emissions = simple_data
    results = calculate_emission_intensity(hc_export, emissions, Frequency.NONE)
    assert len(results.results) == 1
    res = results.results[0]

    # Cumulative: emission/hc_export = [2, 2, 2] as emission is 2 * hc_export for all steps
    assert all(v == 2 for v in res.intensity_sm3.values)
    # Check conversion to boe
    expected = 2 / boe_factor  # Convert sm3 to boe
    assert all(v == pytest.approx(expected, rel=1e-9) for v in res.intensity_boe.values)

    # Yearly intensity not defined if not yearly frequency
    assert res.intensity_yearly_sm3 is None
    assert res.intensity_yearly_boe is None


def test_resample(simple_data):
    """Test that resampling emission intensity results to yearly frequency works as expected."""
    hc_export, emissions = simple_data
    results = calculate_emission_intensity(hc_export, emissions, Frequency.YEAR)
    resampled = results.resample(Frequency.YEAR)
    assert isinstance(resampled, EmissionIntensityResults)
    assert len(resampled.results) == 1

    # Should still be 2 for all values after resample (since all periods are in the same year)
    assert all(v == 2 for v in resampled.results[0].intensity_sm3.values)

    # Check yearly intensity
    assert all(v == 2 for v in resampled.results[0].intensity_yearly_sm3.values)

    # Check conversion to boe
    expected = 2 / boe_factor  # Convert sm3 to boe
    assert all(v == expected for v in resampled.results[0].intensity_yearly_boe.values)


def test_emission_intensity_to_csv(simple_data):
    """Test that emission intensity results are correctly serialized to CSV format."""
    hc_export, emissions = simple_data
    results = calculate_emission_intensity(hc_export, emissions, Frequency.YEAR)
    results = results.resample(Frequency.YEAR)
    date_time_formats = DateTimeFormats.get_format(int(DateFormat.ISO_8601.value))

    csv_content = emission_intensity_to_csv(results, date_time_formats)
    reader = csv.DictReader(io.StringIO(csv_content))
    rows = list(reader)

    # Check headers match actual output
    expected_headers = {
        "timesteps",
        "co2.intensity_sm3[kg/Sm3]",
        "co2.intensity_boe[kg/BOE]",
        "co2.intensity_yearly_sm3[kg/Sm3]",
        "co2.intensity_yearly_boe[kg/BOE]",
    }
    assert set(reader.fieldnames) == expected_headers

    # Check content
    for row in rows:
        assert float(row["co2.intensity_sm3[kg/Sm3]"]) == 2
        assert float(row["co2.intensity_boe[kg/BOE]"]) == pytest.approx(2 / boe_factor, rel=1e-9)


def test_emission_intensity_to_json(simple_data):
    """Test that emission intensity results are correctly serialized to JSON format."""
    hc_export, emissions = simple_data
    results = calculate_emission_intensity(hc_export, emissions, Frequency.YEAR)
    results = results.resample(Frequency.YEAR)

    # Use model_dump_json as in CLI
    json_content = results.model_dump_json()
    data = json.loads(json_content)

    # Check structure
    assert isinstance(data, dict)
    assert "results" in data
    assert isinstance(data["results"], list)
    for entry in data["results"]:
        assert "intensity_sm3" in entry
        assert all(v == 2 for v in entry["intensity_sm3"]["values"])
        assert "intensity_boe" in entry
        for v in entry["intensity_boe"]["values"]:
            assert v == pytest.approx(2 / boe_factor, rel=1e-9)
