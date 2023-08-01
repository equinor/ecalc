import csv
import json
from datetime import date
from io import StringIO
from os.path import getsize
from pathlib import Path
from typing import Literal, NamedTuple

import pandas as pd
import pytest
import yaml
from cli import main
from cli.commands import show
from libecalc.common.exceptions import EcalcError
from libecalc.common.run_info import RunInfo
from libecalc.dto.utils.validators import COMPONENT_NAME_ALLOWED_CHARS
from libecalc.examples import advanced, simple
from libecalc.fixtures.cases import ltp_export
from libecalc.input.yaml.yaml_models.pyyaml_yaml_model import PyYamlYamlModel
from libecalc.input.yaml_entities import ResourceStream
from pydantic import Protocol
from typer.testing import CliRunner

runner = CliRunner()


@pytest.fixture(scope="session")
def simple_yaml_path():
    return (Path(simple.__file__).parent / "model.yaml").absolute()


@pytest.fixture(scope="session")
def simple_temporal_yaml_path():
    return (Path(simple.__file__).parent / "model_temporal.yaml").absolute()


@pytest.fixture(scope="session")
def simple_duplicate_names_yaml_path():
    return (Path(simple.__file__).parent / "model_duplicate_names.yaml").absolute()


@pytest.fixture(scope="session")
def simple_multiple_energy_models_yaml_path():
    return (Path(simple.__file__).parent / "model_multiple_energy_models_one_consumer.yaml").absolute()


@pytest.fixture(scope="session")
def simple_duplicate_emissions_yaml_path():
    return (Path(simple.__file__).parent / "model_duplicate_emissions_in_fuel.yaml").absolute()


@pytest.fixture(scope="session")
def advanced_yaml_path():
    return (Path(advanced.__file__).parent / "model.yaml").absolute()


@pytest.fixture
def ltp_data_path():
    return Path(ltp_export.__file__).parent / "data"


@pytest.fixture
def ltp_yaml_path(ltp_data_path):
    return (ltp_data_path / "ltp_export.yaml").absolute()


def _get_args(
    model_file: Path,
    output_folder: Path = None,
    csv: bool = False,
    name_prefix: str = None,
    json: bool = False,
    detailed_output: bool = True,
    ltp_export: bool = False,
    stp_export: bool = False,
    output_frequency: Literal["NONE", "DAY", "MONTH", "YEAR"] = None,
    flow_diagram: bool = False,
    date_format_option: int = None,
    logs_folder: Path = None,
):
    args = []

    if logs_folder is not None:
        args.append("--log-folder")
        args.append(str(logs_folder))

    args.append("run")
    args.append(str(model_file))

    if output_folder is not None:
        args.append("--outputfolder")
        args.append(str(output_folder))

    if not csv:
        args.append("--csv")

    if json:
        args.append("--json")

    if name_prefix is not None:
        args.append("--nameprefix")
        args.append(name_prefix)

    if detailed_output:
        args.append("--detailedoutput")

    if ltp_export:
        args.append("--ltp-export")
    if stp_export:
        args.append("--stp-export")
    if output_frequency is not None:
        args.append("--outputfrequency")
        args.append(output_frequency)

    if flow_diagram:
        args.append("--flow-diagram")

    if date_format_option is not None:
        args.append("--date-format-option")
        args.append(str(date_format_option))

    return args


class EcalcTestRun(NamedTuple):
    output_folder: Path


@pytest.fixture(scope="session")
def simple_run(tmp_path_factory, monkeypatch_session, simple_yaml_path):
    tmp_path = tmp_path_factory.mktemp("outputdir")
    runner.invoke(
        main.app,
        _get_args(model_file=simple_yaml_path, output_folder=tmp_path),
        catch_exceptions=False,
    )
    return EcalcTestRun(output_folder=tmp_path)


class TestCsvOutput:
    def test_no_csv(self, simple_yaml_path, tmp_path):
        name_prefix = "test"
        runner.invoke(
            main.app,
            _get_args(model_file=simple_yaml_path, csv=False, output_folder=tmp_path, name_prefix=name_prefix),
            catch_exceptions=False,
        )
        csv_output_file = tmp_path / f"{name_prefix}.csv"
        assert not csv_output_file.is_file()

    @pytest.mark.snapshot
    def test_csv_default(self, simple_yaml_path, tmp_path, snapshot):
        run_name_prefix = "test"
        runner.invoke(
            main.app,
            _get_args(model_file=simple_yaml_path, csv=True, output_folder=tmp_path, name_prefix=run_name_prefix),
            catch_exceptions=False,
        )

        run_csv_output_file = tmp_path / f"{run_name_prefix}.csv"
        assert run_csv_output_file.is_file()
        with open(run_csv_output_file) as csv_file:
            csv_data = csv_file.read()
            snapshot.assert_match(csv_data, snapshot_name=run_csv_output_file.name)

    @pytest.mark.snapshot
    def test_csv_temporal_default(self, simple_temporal_yaml_path, simple_yaml_path, tmp_path, snapshot):
        """
        Check that reindex works and results are correct when using temporal models.
        The temporal model is simple, and should not change the results compared to
        the basic model.
        """

        run_name_prefix = "test"
        run_name_prefix_temporal = "test_temporal"

        runner.invoke(
            main.app,
            _get_args(
                model_file=simple_yaml_path,
                csv=True,
                output_folder=tmp_path,
                name_prefix=run_name_prefix,
                output_frequency="YEAR",
            ),
            catch_exceptions=False,
        )

        runner.invoke(
            main.app,
            _get_args(
                model_file=simple_temporal_yaml_path,
                csv=True,
                output_folder=tmp_path,
                name_prefix=run_name_prefix_temporal,
                output_frequency="YEAR",
            ),
            catch_exceptions=False,
        )
        run_csv_output_file = tmp_path / f"{run_name_prefix}.csv"
        run_csv_temporal_output_file = tmp_path / f"{run_name_prefix_temporal}.csv"

        assert run_csv_output_file.is_file()
        assert run_csv_temporal_output_file.is_file()
        csv_file = open(run_csv_output_file).read()
        csv_temporal_file = open(run_csv_temporal_output_file).read()

        # First check that snapshots are ok
        snapshot.assert_match(csv_file, snapshot_name=run_csv_output_file.name)
        snapshot.assert_match(csv_temporal_file, snapshot_name=run_csv_temporal_output_file.name)

        # Then compare with- and without temporal model, result should be the same;
        # only column name is different due to different yaml-files.
        df_basic = pd.read_csv(run_csv_output_file)
        df_temporal = pd.read_csv(run_csv_temporal_output_file)

        # Rename column names to make headings identical, before comparing
        df_temporal.columns = df_temporal.columns.str.replace("model_temporal", "model")

        assert df_temporal.equals(df_basic)

    def test_operational_settings_used_available(self, advanced_yaml_path, tmp_path):
        """Check that we are providing operational settings used for systems."""
        run_name_prefix = "operational_settings_used"
        runner.invoke(
            main.app,
            _get_args(model_file=advanced_yaml_path, csv=True, output_folder=tmp_path, name_prefix=run_name_prefix),
            catch_exceptions=False,
        )
        run_csv_output_file = tmp_path / f"{run_name_prefix}.csv"
        assert run_csv_output_file.is_file()
        df = pd.read_csv(run_csv_output_file, index_col="timesteps")
        operational_settings_used = df["Water injection pump system A.operational_settings_used[N/A]"].tolist()
        is_valid = df["Water injection pump system A.is_valid[N/A]"].tolist()
        assert operational_settings_used == [3, 3, 3, 3, 3, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
        assert is_valid == [1] * len(operational_settings_used)


class TestJsonOutput:
    def test_json_false(self, simple_yaml_path, tmp_path):
        name_prefix = "test"
        runner.invoke(
            main.app,
            _get_args(
                model_file=simple_yaml_path,
                json=False,
                output_folder=tmp_path,
                name_prefix=name_prefix,
            ),
            catch_exceptions=False,
        )
        json_output_file = tmp_path / f"{name_prefix}.json"
        assert not json_output_file.is_file()

    @pytest.mark.snapshot
    def test_json_true(self, simple_yaml_path, tmp_path, snapshot):
        run_name_prefix = "test"
        runner.invoke(
            main.app,
            _get_args(
                model_file=simple_yaml_path,
                json=True,
                output_folder=tmp_path,
                name_prefix=run_name_prefix,
            ),
            catch_exceptions=False,
        )

        v3_json_actual_path = tmp_path / f"{run_name_prefix}_v3.json"
        assert v3_json_actual_path.is_file()
        with open(v3_json_actual_path) as json_file:
            json_data = json.loads(json_file.read())
        snapshot.assert_match(
            json.dumps(json_data, sort_keys=True, indent=2, default=str), snapshot_name=v3_json_actual_path.name
        )

        run_info_actual_path = tmp_path / f"{run_name_prefix}_run_info.json"
        assert run_info_actual_path.is_file()
        assert RunInfo.parse_file(run_info_actual_path, proto=Protocol.json)

    @pytest.mark.snapshot
    def test_json_true_detailed_output(self, simple_yaml_path, tmp_path, snapshot):
        run_name_prefix = "test_full_json"
        runner.invoke(
            main.app,
            _get_args(
                model_file=simple_yaml_path,
                json=True,
                output_folder=tmp_path,
                name_prefix=run_name_prefix,
                detailed_output=True,
            ),
            catch_exceptions=False,
        )

        v3_json_actual_path = tmp_path / f"{run_name_prefix}_v3.json"
        assert v3_json_actual_path.is_file()
        with open(v3_json_actual_path) as json_file:
            json_data = json.loads(json_file.read())
        snapshot.assert_match(
            json.dumps(json_data, sort_keys=True, indent=2, default=str), snapshot_name=v3_json_actual_path.name
        )


class TestLtpExport:
    @pytest.mark.snapshot
    def test_new_ltp_export_properly(self, ltp_yaml_path, tmp_path, snapshot):
        """This test is testing on the "official" LTP setup, ie. required categories
        and naming conventions, etc in order to get a correct result.
        """
        run_name_prefix = "test"
        runner.invoke(
            main.app,
            _get_args(
                model_file=Path(ltp_yaml_path),
                ltp_export=True,
                output_folder=tmp_path,
                name_prefix=run_name_prefix,
                csv=False,
                output_frequency="YEAR",
            ),
            catch_exceptions=False,
        )

        # NOTE
        # if the data frames are different, use df.compare(other_df) for details

        # Note: "Hardcoded" installation names for this special case. Make sure all are compared
        installation_names = [
            "INST_A",
            "MOBILE_HOST_FIELD",
            "MOBILE_SATELLITE_A",
            "MOBILE_SATELLITE_B",
            "POWER_FROM_SHORE_EVENT",
        ]

        # assert that new files are there
        run_files = [
            tmp_path / f"{run_name_prefix}.{installation_name}.ltp.tsv" for installation_name in installation_names
        ]

        for run_file in run_files:
            assert run_file.is_file()

        # Test special LTP files
        for run_file in run_files:
            with open(run_file) as tsv_file:
                tsv_data = tsv_file.read()
                snapshot.assert_match(tsv_data, snapshot_name=run_file.name)

                tsv_file.seek(0)
                df = pd.read_csv(tsv_file, sep="\t")
                snapshot.assert_match(df.to_json(indent=2), snapshot_name=f"{run_file.name}.json")


class TestStpExport:
    @pytest.mark.snapshot
    def test_new_stp_export_properly(self, ltp_yaml_path, tmp_path, snapshot):
        """This test is testing on the "official" STP setup, ie. required categories
        and naming conventions, etc in order to get a correct result.
        """
        run_name_prefix = "test"
        runner.invoke(
            main.app,
            _get_args(
                model_file=Path(ltp_yaml_path),
                stp_export=True,
                output_folder=tmp_path,
                name_prefix=run_name_prefix,
                csv=False,
                output_frequency="MONTH",
            ),
            catch_exceptions=False,
        )

        # NOTE
        # if the data frames are different, use df.compare(other_df) for details

        # Note: "Hardcoded" installation names for this special case. Make sure all are compared
        installation_names = [
            "INST_A",
            "MOBILE_HOST_FIELD",
            "MOBILE_SATELLITE_A",
            "MOBILE_SATELLITE_B",
            "POWER_FROM_SHORE_EVENT",
        ]

        # assert that new files are there
        run_files = [
            tmp_path / f"{run_name_prefix}.{installation_name}.stp.tsv" for installation_name in installation_names
        ]

        for run_file in run_files:
            assert run_file.is_file()

        # Test special STP files
        for run_file in run_files:
            with open(run_file) as tsv_file:
                tsv_data = tsv_file.read()
                snapshot.assert_match(tsv_data, snapshot_name=run_file.name)

                tsv_file.seek(0)
                df = pd.read_csv(tsv_file, sep="\t")
                snapshot.assert_match(df.to_json(indent=2), snapshot_name=f"{run_file.name}.json")


class TestFlowDiagramOutput:
    @pytest.mark.snapshot
    def test_valid(self, simple_yaml_path, tmp_path, snapshot):
        runner.invoke(
            main.app,
            _get_args(model_file=simple_yaml_path, output_folder=tmp_path, name_prefix="", flow_diagram=True),
            catch_exceptions=False,
        )
        flow_diagram_filepath = tmp_path / "flow-diagram.json"
        content_text = flow_diagram_filepath.read_text()
        content = json.loads(content_text)
        snapshot.assert_match(
            json.dumps(content, sort_keys=True, indent=4, default=str), snapshot_name="flow-diagram.json"
        )


class TestLogFileOutput:
    def test_save_logs(self, simple_yaml_path, tmp_path, snapshot):
        run_name_prefix = "test"
        runner.invoke(
            main.app,
            _get_args(
                model_file=simple_yaml_path,
                output_folder=tmp_path,
                name_prefix=run_name_prefix,
                logs_folder=tmp_path,
            ),
            catch_exceptions=False,
        )

        log_file_actual_path = tmp_path / f"{date.today()}_debug.log"
        assert log_file_actual_path.is_file()
        assert getsize(log_file_actual_path) > 0


class TestShowResultsCommand:
    @pytest.mark.snapshot
    def test_component_name_json(self, simple_run, monkeypatch, snapshot, tmp_path):
        monkeypatch.chdir(tmp_path)

        runner.invoke(
            show.app,
            [
                "results",
                "--name",
                "Sea water injection pump",
                "--output-format",
                "json",
                "--detailed-output",
                "--output-folder",
                str(simple_run.output_folder),
                "--file",
                "./waterinj.json",
            ],
            catch_exceptions=False,
        )

        with open("./waterinj.json") as waterinj_result:
            waterinj_data = json.load(waterinj_result)
            snapshot.assert_match(json.dumps(waterinj_data, sort_keys=True, indent=4), snapshot_name="waterinj.json")

    @pytest.mark.snapshot
    def test_component_name_json_stdout(self, simple_run, monkeypatch, snapshot):
        result = runner.invoke(
            show.app,
            [
                "results",
                "--name",
                "Sea water injection pump",
                "--output-format",
                "json",
                "--detailed-output",
                "--output-folder",
                str(simple_run.output_folder),
            ],
            catch_exceptions=False,
        )
        output_text = result.stdout
        waterinj_data = json.loads(output_text)
        snapshot.assert_match(json.dumps(waterinj_data, sort_keys=True, indent=4), snapshot_name="waterinj.json")

    @pytest.mark.snapshot
    def test_component_name_csv(self, simple_run, monkeypatch, snapshot, tmp_path):
        monkeypatch.chdir(tmp_path)

        runner.invoke(
            show.app,
            [
                "results",
                "--name",
                "Sea water injection pump",
                "--output-format",
                "csv",
                "--detailed-output",
                "--output-folder",
                str(simple_run.output_folder),
                "--file",
                "./waterinj.csv",
            ],
            catch_exceptions=False,
        )

        with open("./waterinj.csv") as waterinj_result:
            waterinj_data = waterinj_result.read()
            snapshot.assert_match(waterinj_data, snapshot_name="waterinj.csv")

    @pytest.mark.snapshot
    def test_full_csv(self, simple_run, monkeypatch, snapshot):
        result = runner.invoke(
            show.app,
            [
                "results",
                "--output-format",
                "csv",
                "--output-folder",
                str(simple_run.output_folder),
            ],
            catch_exceptions=False,
        )

        output_text = result.stdout
        snapshot.assert_match(output_text, snapshot_name="results.csv")

    @pytest.mark.snapshot
    def test_csv_resampled(self, simple_run, monkeypatch, snapshot):
        result = runner.invoke(
            show.app,
            [
                "results",
                "--output-format",
                "csv",
                "--output-folder",
                str(simple_run.output_folder),
                "--output-frequency",
                "YEAR",
            ],
            catch_exceptions=False,
        )

        output_text = result.stdout
        snapshot.assert_match(output_text, snapshot_name="results_resampled.csv")

    @pytest.mark.snapshot
    def test_json_resampled(self, simple_run, monkeypatch, snapshot):
        """
        TEST REASON and SCOPE: That resampled json follows json schema

        Testing the resample json from a representative model in order to make
        sure that the resampled json is correctly changing the json according to
        our schema. Not testing this may easily lead to json that violates the schema
        when e.g. new data types are introduced. This test should make sure we have
        control of that. This was added after a bug in resampling was found, where
        resampling was creating different json than without resampling, and that
        the json was invalid.

        Args:
            simple_run:
            monkeypatch:
            snapshot:

        Returns:

        """
        result = runner.invoke(
            show.app,
            [
                "results",
                "--output-format",
                "json",
                "--output-folder",
                str(simple_run.output_folder),
                "--output-frequency",
                "YEAR",
            ],
            catch_exceptions=False,
        )

        output_text = result.stdout
        snapshot.assert_match(output_text, snapshot_name="results_resampled.json")

    def test_json_custom_date_format(self, simple_run, monkeypatch, snapshot):
        result = runner.invoke(
            show.app,
            [
                "results",
                "--output-format",
                "json",
                "--detailed-output",
                "--output-folder",
                str(simple_run.output_folder),
                "--date-format-option",
                "2",
            ],
            catch_exceptions=False,
        )

        output_text = result.stdout
        data = json.loads(output_text)
        assert data["component_result"]["timesteps"] == [
            "01.01.2020 00:00:00",
            "01.01.2021 00:00:00",
            "01.01.2022 00:00:00",
            "01.01.2023 00:00:00",
            "01.01.2024 00:00:00",
            "01.12.2024 00:00:00",
            "01.01.2026 00:00:00",
            "01.01.2027 00:00:00",
            "01.01.2028 00:00:00",
            "01.01.2029 00:00:00",
            "01.01.2030 00:00:00",
            "01.01.2031 00:00:00",
        ]

    def test_csv_custom_date_format(self, simple_run, monkeypatch, snapshot):
        result = runner.invoke(
            show.app,
            [
                "results",
                "--output-format",
                "csv",
                "--output-folder",
                str(simple_run.output_folder),
                "--date-format-option",
                "2",
            ],
            catch_exceptions=False,
        )

        output_text = result.stdout
        data = csv.reader(StringIO(output_text), delimiter=",")
        timesteps = [row[0] for row in list(data)[1:]]
        assert timesteps == [
            "01.01.2020 00:00:00",
            "01.01.2021 00:00:00",
            "01.01.2022 00:00:00",
            "01.01.2023 00:00:00",
            "01.01.2024 00:00:00",
            "01.12.2024 00:00:00",
            "01.01.2026 00:00:00",
            "01.01.2027 00:00:00",
            "01.01.2028 00:00:00",
            "01.01.2029 00:00:00",
            "01.01.2030 00:00:00",
            "01.01.2031 00:00:00",
        ]

    @pytest.mark.snapshot
    def test_full_simplified_json(self, simple_run, monkeypatch, snapshot):
        result = runner.invoke(
            show.app,
            ["results", "--output-format", "json", "--output-folder", str(simple_run.output_folder)],
            catch_exceptions=False,
        )

        output_text = result.stdout
        snapshot.assert_match(output_text, snapshot_name="results.json")


class TestYamlFile:
    def test_yaml_file_error(self):
        """
        TEST SCOPE: Check error message when Yaml file name is wrong.

        A file name with ´.´ in the file stem should not be accepted. The error message
        should be understandable for the user.

        Args:
            simple model file with bad name:

        Returns:

        """

        yaml_wrong_name = (Path("test.name.yaml")).absolute()
        yaml_reader = PyYamlYamlModel.YamlReader(loader=yaml.SafeLoader)
        stream = StringIO("")
        yaml_stream = ResourceStream(name=yaml_wrong_name.name, stream=stream)

        with pytest.raises(EcalcError) as ee:
            yaml_reader.load(yaml_file=yaml_stream)

        assert (
            f"The model file, {yaml_wrong_name.name}, contains illegal special characters. "
            f"Allowed characters are {COMPONENT_NAME_ALLOWED_CHARS}" in str(ee.value)
        )

    def test_yaml_duplicate_fuel(self, simple_duplicate_names_yaml_path, tmp_path):
        """
        TEST SCOPE: Check that duplicate fuel type names are not allowed in Yaml file.

        Args:
            simple model file with duplicate fuel names:

        Returns:

        """
        with pytest.raises(ValueError) as exc_info:
            runner.invoke(
                main.app,
                _get_args(
                    model_file=simple_duplicate_names_yaml_path,
                    csv=True,
                    output_folder=tmp_path,
                    name_prefix="test",
                    output_frequency="YEAR",
                ),
                catch_exceptions=False,
            )

        assert "Duplicated names are: fuel_gas" in str(exc_info.value)

    def test_yaml_duplicate_emissions_in_fuel(self, simple_duplicate_emissions_yaml_path, tmp_path):
        """
        TEST SCOPE: Check that duplicate emission names for one fuel type are not allowed in Yaml file.

        Args:
            simple model file with duplicate emission names:

        Returns:

        """
        with pytest.raises(ValueError) as exc_info:
            runner.invoke(
                main.app,
                _get_args(
                    model_file=simple_duplicate_emissions_yaml_path,
                    csv=True,
                    output_folder=tmp_path,
                    name_prefix="test",
                    output_frequency="YEAR",
                ),
                catch_exceptions=False,
            )

        assert "Emission names must be unique for each fuel type. " "Duplicated names are: CO2,CH4" in str(
            exc_info.value
        )

    def test_yaml_multiple_energy_models_one_consumer(self, simple_multiple_energy_models_yaml_path, tmp_path):
        """
        TEST SCOPE: Check that multiple energy models for one consumer are not allowed in Yaml file.

        Args:
            simple model file with energy models for one consumer:

        Returns:

        """
        with pytest.raises(ValueError) as exc_info:
            runner.invoke(
                main.app,
                _get_args(
                    model_file=simple_multiple_energy_models_yaml_path,
                    csv=True,
                    output_folder=tmp_path,
                    name_prefix="test",
                    output_frequency="YEAR",
                ),
                catch_exceptions=False,
            )

        assert (
            "Energy model type cannot change over time within a single consumer. "
            "The model type is changed for gasinj: ['DIRECT', 'COMPRESSOR']" in str(exc_info.value)
        )
