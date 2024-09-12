from pathlib import Path

from libecalc.presentation.yaml.configuration_service import ConfigurationService
from libecalc.presentation.yaml.yaml_entities import ResourceStream
from libecalc.presentation.yaml.yaml_models.yaml_model import ReaderType, YamlConfiguration, YamlValidator


class FileConfigurationService(ConfigurationService):
    """
    A configuration service that reads the configuration from file.
    """

    def __init__(self, configuration_path: Path):
        self._configuration_path = configuration_path

    def get_configuration(self) -> YamlValidator:
        with open(self._configuration_path) as configuration_file:
            main_resource = ResourceStream(
                name=self._configuration_path.stem,
                stream=configuration_file,
            )

            main_yaml_model = YamlConfiguration.Builder.get_yaml_reader(ReaderType.PYYAML).get_validator(
                main_yaml=main_resource, enable_include=True, base_dir=self._configuration_path.parent
            )
            return main_yaml_model
