import abc
from typing import Dict, Protocol

from libecalc.presentation.yaml.resource import Resource
from libecalc.presentation.yaml.yaml_models.yaml_model import YamlValidator


class ResourceService(Protocol):
    """
    A service to get a resource
    """

    @abc.abstractmethod
    def get_resources(self, configuration: YamlValidator) -> Dict[str, Resource]: ...