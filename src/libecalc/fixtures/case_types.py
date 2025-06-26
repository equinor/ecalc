import io
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

from ecalc_cli.infrastructure.file_resource_service import FileResourceService
from libecalc.common.time_utils import Frequency
from libecalc.presentation.yaml.file_configuration_service import FileConfigurationService
from libecalc.presentation.yaml.model import YamlModel
from libecalc.presentation.yaml.yaml_entities import MemoryResource


@dataclass
class YamlCase:
    resources: dict[str, MemoryResource]
    main_file_path: Path

    @property
    def main_file(self) -> TextIO:
        with open(self.main_file_path) as f:
            lines = f.read()
            return io.StringIO(lines)

    def get_yaml_model(self, frequency: Frequency = Frequency.NONE) -> YamlModel:
        configuration_service = FileConfigurationService(self.main_file_path)
        configuration = configuration_service.get_configuration()
        resource_service = FileResourceService(self.main_file_path.parent, configuration=configuration)
        return YamlModel(
            configuration=configuration,
            resource_service=resource_service,
            output_frequency=frequency,
        )
