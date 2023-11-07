from libecalc.presentation.yaml.mappers import _sort_models
from libecalc.presentation.yaml.yaml_keywords import EcalcYamlKeywords


class TestCreateReferences:
    @staticmethod
    def test_sort_models():
        models_data = [
            {
                EcalcYamlKeywords.name: "a",
                EcalcYamlKeywords.type: EcalcYamlKeywords.models_type_compressor_with_turbine,
            },
            {
                EcalcYamlKeywords.name: "b",
                EcalcYamlKeywords.type: EcalcYamlKeywords.models_type_compressor_train_simplified,
            },
            {EcalcYamlKeywords.name: "c", EcalcYamlKeywords.type: EcalcYamlKeywords.models_type_turbine},
            {
                EcalcYamlKeywords.name: "d",
                EcalcYamlKeywords.type: EcalcYamlKeywords.models_type_compressor_with_turbine,
            },
            {EcalcYamlKeywords.name: "e", EcalcYamlKeywords.type: EcalcYamlKeywords.models_type_compressor_chart},
            {
                EcalcYamlKeywords.name: "f",
                EcalcYamlKeywords.type: EcalcYamlKeywords.models_type_compressor_train_simplified,
            },
            {EcalcYamlKeywords.name: "g", EcalcYamlKeywords.type: EcalcYamlKeywords.models_type_compressor_chart},
            {
                EcalcYamlKeywords.name: "h",
                EcalcYamlKeywords.type: EcalcYamlKeywords.models_type_compressor_train_simplified,
            },
            {EcalcYamlKeywords.name: "i", EcalcYamlKeywords.type: EcalcYamlKeywords.models_type_compressor_chart},
        ]

        sorted_models = _sort_models(models_data)
        assert [sorted_model[EcalcYamlKeywords.name] for sorted_model in sorted_models] == [
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
