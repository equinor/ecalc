from typing import Optional, cast

from libecalc.presentation.yaml.configuration_service import ConfigurationService
from libecalc.presentation.yaml.yaml_entities import ResourceStream
from libecalc.presentation.yaml.yaml_models.yaml_model import ReaderType, YamlConfiguration, YamlValidator


class OverridableStreamConfigurationService(ConfigurationService):
    def __init__(self, stream: ResourceStream, overrides: Optional[dict] = None):
        self._overrides = overrides
        self._stream = stream

    def get_configuration(self) -> YamlValidator:
        main_yaml_model = YamlConfiguration.Builder.get_yaml_reader(ReaderType.PYYAML).read(
            main_yaml=self._stream,
            enable_include=True,
        )

        if self._overrides is not None:
            main_yaml_model._internal_datamodel.update(self._overrides)
        return cast(YamlValidator, main_yaml_model)
