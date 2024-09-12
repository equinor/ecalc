from typing import Dict

from libecalc.common.time_utils import Frequency
from libecalc.fixtures import DTOCase, YamlCase
from libecalc.presentation.yaml.file_configuration_service import FileConfigurationService
from libecalc.presentation.yaml.model import YamlModel
from libecalc.presentation.yaml.resource_service import ResourceService
from libecalc.presentation.yaml.yaml_entities import MemoryResource
from libecalc.presentation.yaml.yaml_models.yaml_model import YamlValidator


class DirectResourceService(ResourceService):
    def __init__(self, resources: Dict[str, MemoryResource]):
        self._resources = resources

    def get_resources(self, configuration: YamlValidator) -> Dict[str, MemoryResource]:
        return self._resources


class TestParseYaml:
    def test_parse_input_with_all_energy_usage_models(
        self, all_energy_usage_models_yaml: YamlCase, all_energy_usage_models_dto: DTOCase
    ):
        """
        Make sure yaml and dto is consistent for all_energy_usage_models
        """
        configuration_service = FileConfigurationService(configuration_path=all_energy_usage_models_yaml.main_file_path)
        resource_service = DirectResourceService(resources=all_energy_usage_models_yaml.resources)
        model = YamlModel(
            configuration_service=configuration_service,
            resource_service=resource_service,
            output_frequency=Frequency.NONE,
        )

        assert model.dto.model_dump() == all_energy_usage_models_dto.ecalc_model.model_dump()
        assert model.variables == all_energy_usage_models_dto.variables

    def test_parse_input_with_consumer_system_v2(self, consumer_system_v2_yaml, consumer_system_v2_dto_fixture):
        """
        Make sure yaml and dto is consistent for consumer_system_v2
        """
        configuration_service = FileConfigurationService(configuration_path=consumer_system_v2_yaml.main_file_path)
        resource_service = DirectResourceService(resources=consumer_system_v2_yaml.resources)
        model = YamlModel(
            configuration_service=configuration_service,
            resource_service=resource_service,
            output_frequency=Frequency.NONE,
        )

        assert model.dto.model_dump() == consumer_system_v2_dto_fixture.ecalc_model.model_dump()
        assert model.variables == consumer_system_v2_dto_fixture.variables
