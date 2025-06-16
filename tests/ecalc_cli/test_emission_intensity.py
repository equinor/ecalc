import csv
import io
import json
from datetime import datetime

import pytest
from typer.testing import CliRunner

from ecalc_cli import main
from ecalc_cli.emission_intensity import EmissionIntensityCalculator
from ecalc_cli.io.output import emission_intensity_to_csv
from ecalc_cli.types import DateFormat
from libecalc.common.datetime.utils import DateTimeFormats
from libecalc.common.time_utils import Frequency

runner = CliRunner()
boe_factor = 6.29


def test_emission_intensity_to_csv(simple_emission_data):
    """Test that emission intensity results are correctly serialized to CSV format."""
    hc_export, emissions = simple_emission_data
    emission_intensity_calculator = EmissionIntensityCalculator(hc_export, emissions, Frequency.YEAR)
    results = emission_intensity_calculator.get_results()
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
        assert float(row["co2.intensity_boe[kg/BOE]"]) == pytest.approx(round(2 / boe_factor, 5))


def test_emission_intensity_to_json(simple_emission_data):
    """Test that emission intensity results are correctly serialized to JSON format."""
    hc_export, emissions = simple_emission_data
    emission_intensity_calculator = EmissionIntensityCalculator(hc_export, emissions, Frequency.NONE)
    results = emission_intensity_calculator.get_results()

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


@pytest.mark.parametrize("frequency", [Frequency.YEAR, Frequency.MONTH, Frequency.NONE])
def test_emission_intensity_with_different_frequencies(simple_emission_data, frequency):
    """Test emission intensity calculation with different frequencies."""
    hc_export, emissions = simple_emission_data
    emission_intensity_calculator = EmissionIntensityCalculator(hc_export, emissions, frequency)
    results = emission_intensity_calculator.get_results()

    assert results is not None
    for result in results.results:
        assert result.intensity_sm3 is not None
        assert result.intensity_boe is not None
        if frequency == Frequency.YEAR:
            assert result.intensity_yearly_sm3 is not None
            assert result.intensity_yearly_boe is not None
        else:
            assert result.intensity_yearly_sm3 is None
            assert result.intensity_yearly_boe is None


def test_cli_with_resampling(simple_emission_data, tmp_path, simple_yaml_path):
    """Test CLI with resampling to ensure it handles input correctly."""

    # Set up the output folder and name prefix
    output_folder = tmp_path
    name_prefix = "test_run"

    # Run the CLI with runner.invoke
    result = runner.invoke(
        main.app,
        [
            "run",
            str(simple_yaml_path),  # Pass MODEL_FILE as a positional argument
            "--json",
            "--output-folder",
            str(output_folder),
            "--name-prefix",
            name_prefix,
            "--outputfrequency",
            "YEAR",
        ],
        catch_exceptions=False,
    )

    # Assert that the CLI ran successfully
    assert result.exit_code == 0, f"CLI failed: {result.output}"

    # Assert that the output files were created
    output_intensity_csv = output_folder / f"{name_prefix}_intensity.csv"
    output_intensity_json = output_folder / f"{name_prefix}_intensity.json"

    assert output_intensity_csv.exists(), "CSV output file was not created"
    assert output_intensity_json.exists(), "JSON output file was not created"

    # Validate the content of the JSON output file
    output_data = json.loads(output_intensity_json.read_text())
    assert "results" in output_data, "Missing 'results' in output"
    for entry in output_data["results"]:
        assert "intensity_sm3" in entry, "Missing 'intensity_sm3' in result"
        assert "intensity_boe" in entry, "Missing 'intensity_boe' in result"
        assert "intensity_yearly_sm3" in entry, "Missing 'intensity_yearly_sm3' in result"
        assert "intensity_yearly_boe" in entry, "Missing 'intensity_yearly_boe' in result"
