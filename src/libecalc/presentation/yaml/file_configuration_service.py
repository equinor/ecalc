from pathlib import Path

from libecalc.presentation.yaml.configuration_service import ConfigurationService
from libecalc.presentation.yaml.model_validation_exception import ModelValidationException
from libecalc.presentation.yaml.validation_errors import Location, ModelValidationError
from libecalc.presentation.yaml.yaml_entities import ResourceStream
from libecalc.presentation.yaml.yaml_models.exceptions import DuplicateKeyError, YamlError
from libecalc.presentation.yaml.yaml_models.yaml_model import ReaderType, YamlConfiguration, YamlValidator


class FileConfigurationService(ConfigurationService):
    """
    A configuration service that reads the configuration from file.
    """

    def __init__(self, configuration_path: Path):
        self._configuration_path = configuration_path

    def get_configuration(self) -> YamlValidator:
        with open(self._configuration_path) as configuration_file:
            try:
                main_resource = ResourceStream(
                    name=self._configuration_path.stem,
                    stream=configuration_file,
                )

                main_yaml_model = YamlConfiguration.Builder.get_yaml_reader(ReaderType.PYYAML).get_validator(
                    main_yaml=main_resource, enable_include=True, base_dir=self._configuration_path.parent
                )
                return main_yaml_model
            except YamlError as e:
                location = Location(keys=[])
                if isinstance(e, DuplicateKeyError):
                    location = Location(keys=[e.key])
                raise ModelValidationException(
                    errors=[
                        ModelValidationError(
                            location=location,
                            message=e.problem,
                            file_context=e.file_context,
                            data=None,
                        )
                    ]
                ) from e
