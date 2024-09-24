from dataclasses import dataclass

from libecalc.presentation.yaml.mappers.create_references import SortableModel, _sort_models
from libecalc.presentation.yaml.yaml_keywords import EcalcYamlKeywords


@dataclass
class Model(SortableModel):
    name: str
    type: str


class TestCreateReferences:
    @staticmethod
    def test_sort_models():
        models_data = [
            Model(name="a", type=EcalcYamlKeywords.models_type_compressor_with_turbine),
            Model(name="b", type=EcalcYamlKeywords.models_type_compressor_train_simplified),
            Model(name="c", type=EcalcYamlKeywords.models_type_turbine),
            Model(name="d", type=EcalcYamlKeywords.models_type_compressor_with_turbine),
            Model(name="e", type=EcalcYamlKeywords.models_type_compressor_chart),
            Model(name="f", type=EcalcYamlKeywords.models_type_compressor_train_simplified),
            Model(name="g", type=EcalcYamlKeywords.models_type_compressor_chart),
            Model(name="h", type=EcalcYamlKeywords.models_type_compressor_train_simplified),
            Model(name="i", type=EcalcYamlKeywords.models_type_compressor_chart),
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
