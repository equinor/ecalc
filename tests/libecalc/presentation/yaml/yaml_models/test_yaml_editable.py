from io import StringIO

import pytest

from libecalc.presentation.yaml.yaml_entities import ResourceStream
from libecalc.presentation.yaml.yaml_models.yaml_editable import DataModelYamlEditor, YamlEditError, YamlReference
from libecalc.presentation.yaml.yaml_models.yaml_model import ReaderType, YamlConfiguration


def _datamodel() -> dict:
    return {
        "TIME_SERIES": [{"NAME": "ts", "TYPE": "DEFAULT", "FILE": "ts.csv"}],
        "FACILITY_INPUTS": [{"NAME": "genset", "TYPE": "ELECTRICITY2FUEL", "FILE": "genset.csv"}],
        "MODELS": [{"NAME": "chart", "CURVES": {"FILE": "chart.csv"}}],
        "DEFINITIONS": {
            "COMPRESSOR_MODELS": {"compressor_model": {"CHART": {"CURVES": {"FILE": "compressor_chart.csv"}}}},
            "TURBINES": {"turbine": {"LOWER_HEATING_VALUE": 38, "CURVE": {"file": "turbine.csv"}}},
            "GENERATORS": {"generator": {"CURVE": {"FILE": "generator.csv"}}},
        },
        "PROCESS_PIPELINES": {
            "pipeline": {"PROCESS_UNITS": [{"MODEL": {"CHART": {"CURVES": {"FILE": "pipeline_chart.csv"}}}}]}
        },
        "ENERGY_NETWORK": {"UNITS": [{"NAME": "compressor", "TYPE": "COMPRESSOR_SAMPLED", "FILE": "sampled.csv"}]},
    }


class TestFindFileReferences:
    def test_finds_nested_references_with_paths(self):
        editor = DataModelYamlEditor({"A": [{"FILE": "x.csv"}, {"B": {"FILE": "y.csv"}}], "FILE": "root.csv"})

        assert editor.find_file_references() == [
            YamlReference(path=("A", 0, "FILE"), value="x.csv"),
            YamlReference(path=("A", 1, "B", "FILE"), value="y.csv"),
            YamlReference(path=("FILE",), value="root.csv"),
        ]

    def test_key_is_case_insensitive_and_path_keeps_original_casing(self):
        editor = DataModelYamlEditor({"a": {"File": "x.csv"}})

        assert editor.find_file_references() == [YamlReference(path=("a", "File"), value="x.csv")]

    def test_no_references(self):
        assert DataModelYamlEditor({"A": [1, 2, {"B": None}]}).find_file_references() == []

    def test_finds_file_references_in_whole_document(self):
        editor = DataModelYamlEditor(_datamodel())

        assert editor.find_file_references() == [
            YamlReference(path=("TIME_SERIES", 0, "FILE"), value="ts.csv"),
            YamlReference(path=("FACILITY_INPUTS", 0, "FILE"), value="genset.csv"),
            YamlReference(path=("MODELS", 0, "CURVES", "FILE"), value="chart.csv"),
            YamlReference(
                path=("DEFINITIONS", "COMPRESSOR_MODELS", "compressor_model", "CHART", "CURVES", "FILE"),
                value="compressor_chart.csv",
            ),
            YamlReference(path=("DEFINITIONS", "TURBINES", "turbine", "CURVE", "file"), value="turbine.csv"),
            YamlReference(path=("DEFINITIONS", "GENERATORS", "generator", "CURVE", "FILE"), value="generator.csv"),
            YamlReference(
                path=("PROCESS_PIPELINES", "pipeline", "PROCESS_UNITS", 0, "MODEL", "CHART", "CURVES", "FILE"),
                value="pipeline_chart.csv",
            ),
            YamlReference(path=("ENERGY_NETWORK", "UNITS", 0, "FILE"), value="sampled.csv"),
        ]

    def test_ignores_non_string_file_values(self):
        editor = DataModelYamlEditor({"A": {"FILE": None}, "B": {"FILE": ["x.csv"]}})

        assert editor.find_file_references() == []


class TestEdit:
    def test_edit_replaces_value_at_path(self):
        datamodel = _datamodel()
        editor = DataModelYamlEditor(datamodel)
        reference = next(ref for ref in editor.find_file_references() if ref.value == "turbine.csv")

        edited = editor.edit(reference, "resources_turbine.csv")

        assert edited == YamlReference(path=reference.path, value="resources_turbine.csv")
        assert datamodel["DEFINITIONS"]["TURBINES"]["turbine"]["CURVE"]["file"] == "resources_turbine.csv"
        assert datamodel["DEFINITIONS"]["TURBINES"]["turbine"]["LOWER_HEATING_VALUE"] == 38

    def test_edit_in_list(self):
        datamodel = _datamodel()
        editor = DataModelYamlEditor(datamodel)

        editor.edit(YamlReference(path=("ENERGY_NETWORK", "UNITS", 0, "FILE"), value="sampled.csv"), "new.csv")

        assert datamodel["ENERGY_NETWORK"]["UNITS"][0]["FILE"] == "new.csv"

    def test_edit_stale_reference_raises(self):
        editor = DataModelYamlEditor(_datamodel())
        reference = YamlReference(path=("TIME_SERIES", 0, "FILE"), value="ts.csv")
        editor.edit(reference, "other.csv")

        with pytest.raises(YamlEditError, match="Value has changed"):
            editor.edit(reference, "third.csv")

    @pytest.mark.parametrize(
        "path",
        [
            ("DOES_NOT_EXIST", "FILE"),
            ("TIME_SERIES", 5, "FILE"),
            ("TIME_SERIES", "0", "FILE"),
            ("TIME_SERIES", 0, "NOT_A_KEY"),
            ("TIME_SERIES", 0, "FILE", "deeper"),
        ],
    )
    def test_edit_missing_path_raises(self, path):
        with pytest.raises(YamlEditError, match="Path does not exist"):
            DataModelYamlEditor(_datamodel()).edit(YamlReference(path=path, value="ts.csv"), "x.csv")

    def test_edit_root_raises(self):
        with pytest.raises(YamlEditError, match="root"):
            DataModelYamlEditor(_datamodel()).edit(YamlReference(path=(), value=None), {})


class TestYamlConfigurationAsEditable:
    def test_ruamel_edit_is_dumped_and_preserves_comments(self):
        yaml = """\
# top comment
DEFINITIONS:
  TURBINES:
    turbine:
      LOWER_HEATING_VALUE: 38 # lhv comment
      CURVE:
        FILE: resources/turbine.csv # file comment
"""
        configuration = YamlConfiguration.Builder.get_yaml_reader(ReaderType.RUAMEL).read(
            main_yaml=ResourceStream(stream=StringIO(yaml), name="model.yaml")
        )
        editor = configuration.as_editable()

        (reference,) = editor.find_file_references()
        assert reference == YamlReference(
            path=("DEFINITIONS", "TURBINES", "turbine", "CURVE", "FILE"), value="resources/turbine.csv"
        )

        editor.edit(reference, "resources_turbine.csv")

        assert configuration.dump() == yaml.replace("resources/turbine.csv", "resources_turbine.csv")
