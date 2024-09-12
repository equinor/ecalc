import abc
from typing import Protocol

from libecalc.presentation.yaml.yaml_models.yaml_model import YamlValidator


class ConfigurationService(Protocol):
    """
    A service to get the configuration for the model.
    """

    @abc.abstractmethod
    def get_configuration(self) -> YamlValidator: ...
