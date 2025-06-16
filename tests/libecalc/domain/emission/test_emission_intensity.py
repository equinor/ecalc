import pytest

from ecalc_cli.emission_intensity import EmissionIntensityCalculator
from libecalc.common.time_utils import Frequency

boe_factor = 6.29


def test_correct_intensity(simple_emission_data):
    """Test that emission intensity is calculated correctly for simple input data."""
    hc_export, emissions = simple_emission_data
    emission_intensity_calculator = EmissionIntensityCalculator(hc_export, emissions, Frequency.NONE)
    results = emission_intensity_calculator.get_results()
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
