import io
import math
from io import StringIO
from pathlib import Path
from typing import IO

import pytest
from libecalc.infrastructure import file_io
from libecalc.presentation.yaml import yaml_entities
from libecalc.presentation.yaml.yaml_entities import YamlTimeseriesType
from libecalc.presentation.yaml.yaml_models.pyyaml_yaml_model import PyYamlYamlModel


@pytest.fixture
def timeseries_content() -> str:
    return """DATE,          GAS_LIFT
01.01.2019,    1
01.01.2020,    2
"""


@pytest.fixture
def timeseries_content_missing_value() -> str:
    return """DATE,          GAS_LIFT
01.01.2019,    1
01.01.2020,
"""


@pytest.fixture
def timeseries_resource_with_thousand_spacing(tmp_path):
    file = tmp_path / "timeseries.csv"
    file.write_text(
        """DATE,          GAS_LIFT
           01.01.2019,    10
           01.01.2020,    10 000 """
    )
    return file


@pytest.fixture
def float_precise_csv():
    return io.StringIO(
        """SPEED
0.724
0.704
15435.484
5492.822
"""
    )


class TestReadResourceFromString:
    def test_string(self, timeseries_content):
        resource = file_io.read_resource_from_string(timeseries_content)
        assert resource.headers == ["DATE", "GAS_LIFT"]
        assert resource.data == [["01.01.2019", "01.01.2020"], [1, 2]]

    def test_floating_point_precision(self, float_precise_csv):
        resource = file_io.read_resource_from_string(float_precise_csv)
        assert resource.data[0] == [0.724, 0.704, 15435.484, 5492.822]

    def test_missing_value(self, timeseries_content_missing_value):
        resource = file_io.read_resource_from_string(timeseries_content_missing_value)
        assert resource.data[0] == ["01.01.2019", "01.01.2020"]
        assert resource.data[1][0] == 1
        assert resource.data[1][1] == ""


@pytest.fixture
def timeseries_missing_value_file(tmp_path, timeseries_content_missing_value):
    timeseries_file = tmp_path / "timeseries.csv"
    timeseries_file.write_text(data=timeseries_content_missing_value)
    return timeseries_file


class TestReadTimeseriesResource:
    def test_read_timeseries_missing_value(self, timeseries_missing_value_file):
        resource = file_io.read_timeseries_resource(
            resource_input=timeseries_missing_value_file, timeseries_type=YamlTimeseriesType.DEFAULT
        )
        assert resource.data[0] == ["01.01.2019", "01.01.2020"]
        assert resource.data[1][0] == 1
        assert math.isnan(resource.data[1][1])

    def test_read_timeseries_with_thousand_spacing(self, timeseries_resource_with_thousand_spacing):
        resource = file_io.read_timeseries_resource(
            resource_input=timeseries_resource_with_thousand_spacing, timeseries_type=YamlTimeseriesType.DEFAULT
        )
        assert resource.data[1] == [10, 10000]


@pytest.fixture
def facility_resource_missing_value_file(tmp_path):
    facility_file = tmp_path / "facility.csv"
    facility_file.write_text(
        """POWER,FUEL
1,
"""
    )
    return facility_file


def create_csv_from_line(tmp_path: Path, csv_line: str) -> Path:
    csv_file = tmp_path / "csv_file.csv"
    csv_file.write_text(csv_line)
    return csv_file


@pytest.fixture
def tmp_path_fixture(tmp_path: Path) -> Path:
    return tmp_path


class TestReadFacilityResource:
    def test_no_nans(self, facility_resource_missing_value_file):
        with pytest.raises(ValueError) as exc:
            file_io.read_facility_resource(facility_resource_missing_value_file)
        assert (
            str(exc.value)
            == "csv file contains invalid data at row 1, all headers must be associated with a valid column value"
        )

    @pytest.mark.parametrize(
        "csv_line, is_valid_characters",
        [
            ("aa :, bb", True),
            ("aa ., bb", True),
            ("aa +, bb", True),
            ("aa 0, bb", True),
            ("aa _, bb", True),
            ("aa -, bb", True),
            ("aa /, bb", True),
            ("aa #, bb", True),
            ("aa @, bb", False),
            ("aa %, bb", False),
            ("aa &, bb", False),
            ("aa ?, bb", False),
            ("aa ', bb", False),
            ('aa ", bb', False),
            ("aa )(, bb", False),
            ("aa ][, bb", False),
            ("aa }{, bb", False),
            ("aa ><, bb", False),
        ],
    )  # This is not meant to be extensive, just to test that we have some validation
    def test_valid_characters(self, tmp_path_fixture, csv_line: str, is_valid_characters: bool):
        if is_valid_characters:
            file_io.read_facility_resource(create_csv_from_line(tmp_path_fixture, csv_line))
        else:
            with pytest.raises(ValueError) as e:
                file_io.read_facility_resource(create_csv_from_line(tmp_path_fixture, csv_line))
            assert (
                str(e.value) == "Each header value must start with a letter in the "
                "english alphabet (a-zA-Z). And may only contain letters, spaces, numbers or any of the following "
                "characters [ _ - # + : . , /] "
            )

    def test_missing_headers(self, tmp_path_fixture):
        with pytest.raises(ValueError) as e:
            file_io.read_facility_resource(create_csv_from_line(tmp_path_fixture, "HEADER1        ,,HEADER3"))
        assert str(e.value) == "CSV input file must include header"


@pytest.fixture
def yaml_resource():
    return yaml_entities.ResourceStream(
        stream=StringIO(
            """INSTALLATIONS:
  HCEXPORT: '1.0'
  GENERATORSETS:
    - NAME: genset1
    - NAME: genset2
"""
        ),
        name="main.yaml",
    )


class TestReadYaml:
    def test_read_yaml(self, yaml_resource: yaml_entities.ResourceStream):
        read_yaml = PyYamlYamlModel.read_yaml(yaml_resource)
        assert read_yaml == {
            "INSTALLATIONS": {"HCEXPORT": "1.0", "GENERATORSETS": [{"NAME": "genset1"}, {"NAME": "genset2"}]},
        }

        assert read_yaml.start_mark.line == 0
        assert read_yaml.end_mark.line == 5
        assert read_yaml.start_mark.name == "main.yaml"
        installation = read_yaml["INSTALLATIONS"]
        assert installation.start_mark.line == 1
        assert installation.end_mark.line == 5
        assert installation.start_mark.name == "main.yaml"
        generator_sets = installation["GENERATORSETS"]
        assert generator_sets.start_mark.line == 3
        assert generator_sets.end_mark.line == 5
        assert generator_sets.start_mark.name == "main.yaml"
        generator_set1 = generator_sets[0]
        assert generator_set1.start_mark.line == 3
        assert generator_set1.end_mark.line == 4
        assert generator_set1.start_mark.name == "main.yaml"
        generator_set2 = generator_sets[1]
        assert generator_set2.start_mark.line == 4
        assert generator_set2.end_mark.line == 5
        assert generator_set2.start_mark.name == "main.yaml"

    def test_read_yaml_include(self):
        resources = {
            "included.yaml": StringIO(
                """
        HCEXPORT: '1.0'
        GENERATORSETS:
          - NAME: genset1
          - NAME: genset2
        """
            )
        }

        main_text = """
        INSTALLATIONS: !include included.yaml
        """

        main_yaml = yaml_entities.ResourceStream(
            stream=StringIO(main_text),
            name="main.yaml",
        )

        read_yaml = PyYamlYamlModel.read_yaml(main_yaml=main_yaml, resources=resources)

        assert read_yaml == {
            "INSTALLATIONS": {"HCEXPORT": "1.0", "GENERATORSETS": [{"NAME": "genset1"}, {"NAME": "genset2"}]},
        }

        assert read_yaml.start_mark.line == 1
        assert read_yaml.end_mark.line == 2
        assert read_yaml.start_mark.name == "main.yaml"
        installation = read_yaml["INSTALLATIONS"]
        assert installation.start_mark.line == 1
        assert installation.end_mark.line == 5
        assert installation.start_mark.name == "included.yaml"
        generator_sets = installation["GENERATORSETS"]
        assert generator_sets.start_mark.line == 3
        assert generator_sets.end_mark.line == 5
        assert generator_sets.start_mark.name == "included.yaml"
        generator_set1 = generator_sets[0]
        assert generator_set1.start_mark.line == 3
        assert generator_set1.end_mark.line == 4
        assert generator_set1.start_mark.name == "included.yaml"
        generator_set2 = generator_sets[1]
        assert generator_set2.start_mark.line == 4
        assert generator_set2.end_mark.line == 5
        assert generator_set2.start_mark.name == "included.yaml"

    def test_dump_yaml_include(self, yaml_resource):
        resources = {
            "included.yaml": StringIO(
                """
        HCEXPORT: '1.0'
        GENERATORSETS:
        - NAME: genset1
        - NAME: genset2
        """
            )
        }

        main_yaml = yaml_entities.ResourceStream(
            stream=StringIO("""INSTALLATIONS: !include included.yaml"""),
            name="main.yaml",
        )

        dump_yaml = PyYamlYamlModel.dump_and_load_yaml(main_yaml=main_yaml, resources=resources)
        assert dump_yaml == yaml_resource.stream.getvalue()


def valid_ecalc_file(
    path: Path = Path("example/path/test_file.csv"),
    filename: str = "test_file",
    file: IO = StringIO("Test file content"),
    file_type: file_io.EcalcFileType = file_io.EcalcFileType.CSV,
):
    return file_io.ValidEcalcFile(original_filename=path, filename=filename, file=file, file_type=file_type)


class TestZipUpload:
    def test_find_longest_common_path(self):
        assert (
            file_io.find_longest_common_path(Path("common/unique_file"), Path("common/another_unique_file"))
            == "common/"
        )
        assert (
            file_io.find_longest_common_path(Path("unique_folder/common/file_1"), Path("unique_folder_2/common/file_2"))
            == ""
        )

    def test_rename_duplicates(self):
        duplicates = ["file_a"]
        arbitrary_file_one = valid_ecalc_file(filename="file_a", path=Path("resources/file_a.csv"))
        arbitrary_file_two = valid_ecalc_file(filename="file_a", path=Path("file_a.csv"))
        valid_files = [
            arbitrary_file_one,
            arbitrary_file_two,
        ]

        renamed_files = file_io.rename_duplicates(valid_files=valid_files, duplicates=duplicates)

        assert renamed_files[arbitrary_file_one.original_filename] == "resources_file_a.csv"
        assert renamed_files[arbitrary_file_two.original_filename] == "file_a.csv"

        really_long_path = "this/is/a/really/really/really/long/path/it/is/over/100/characters/long/and/will/get/a/unique/id/file_a.csv"

        arbitrary_file_three = valid_ecalc_file(filename="file_a", path=Path(really_long_path))
        arbitrary_file_four = valid_ecalc_file(filename="file_a", path=Path("file_a.csv"))
        valid_files_long_path = [
            arbitrary_file_three,
            arbitrary_file_four,
        ]

        assert len(str(arbitrary_file_three.original_filename)) >= 100

        renamed_files_two = file_io.rename_duplicates(valid_files=valid_files_long_path, duplicates=duplicates)

        assert (
            renamed_files_two[arbitrary_file_three.original_filename]
            != renamed_files_two[arbitrary_file_four.original_filename]
        )
        assert len(renamed_files_two[arbitrary_file_three.original_filename]) == 100
        assert renamed_files_two[arbitrary_file_three.original_filename][-16:-6] == "file_a.csv"
        assert renamed_files_two[arbitrary_file_four.original_filename] == "file_a.csv"

    def test_make_relative_paths(self):
        main_yaml = valid_ecalc_file(path=Path("main/main.yaml"), filename="main.yaml")

        arbitrary_include_file = valid_ecalc_file(path=Path("resources/file.yaml"), filename="file.yaml")

        files = [main_yaml, arbitrary_include_file]

        relative_paths = file_io.make_relative_paths(files=files, main_yaml=main_yaml)

        assert relative_paths[arbitrary_include_file.original_filename] == "../resources/file.yaml"
        assert relative_paths[main_yaml.original_filename] == "main.yaml"
