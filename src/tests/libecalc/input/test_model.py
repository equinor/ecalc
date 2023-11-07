from libecalc.common.time_utils import Frequency
from libecalc.fixtures import YamlCase
from libecalc.presentation.yaml.model import YamlModel


class TestModel:
    def test_parse_ecalc_model(self, all_energy_usage_models_yaml: YamlCase):
        model = YamlModel(path=all_energy_usage_models_yaml.main_file_path, output_frequency=Frequency.NONE)
        assert model
