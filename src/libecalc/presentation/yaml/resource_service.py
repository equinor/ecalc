import abc
from typing import Protocol

from libecalc.domain.resource import Resource
from libecalc.presentation.yaml.yaml_models.yaml_model import YamlValidator


class ResourceService(Protocol):
    """
    A service to get a resource
    """

    @abc.abstractmethod
    def get_resources(self, configuration: YamlValidator) -> dict[str, Resource]: ...
