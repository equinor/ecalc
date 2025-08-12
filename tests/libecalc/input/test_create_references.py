from dataclasses import dataclass

from libecalc.presentation.yaml.mappers.create_references import _sort_models
from libecalc.presentation.yaml.yaml_types.models.yaml_enums import YamlModelType


@dataclass
class Model:
    name: str
    type: str


class TestCreateReferences:
    @staticmethod
    def test_sort_models():
        models_data = [
            Model(name="a", type=YamlModelType.COMPRESSOR_WITH_TURBINE),
            Model(name="b", type=YamlModelType.SIMPLIFIED_VARIABLE_SPEED_COMPRESSOR_TRAIN),
            Model(name="c", type=YamlModelType.TURBINE),
            Model(name="d", type=YamlModelType.COMPRESSOR_WITH_TURBINE),
            Model(name="e", type=YamlModelType.COMPRESSOR_CHART),
            Model(name="f", type=YamlModelType.SIMPLIFIED_VARIABLE_SPEED_COMPRESSOR_TRAIN),
            Model(name="g", type=YamlModelType.COMPRESSOR_CHART),
            Model(name="h", type=YamlModelType.SIMPLIFIED_VARIABLE_SPEED_COMPRESSOR_TRAIN),
            Model(name="i", type=YamlModelType.COMPRESSOR_CHART),
        ]

        sorted_models = _sort_models(models_data)
        assert [sorted_model.name for sorted_model in sorted_models] == [
            "c",
            "e",
            "g",
            "i",
            "b",
            "f",
            "h",
            "a",
            "d",
        ]
