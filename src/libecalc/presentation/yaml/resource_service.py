import abc
from typing import Protocol

from libecalc.presentation.yaml.resource import Resource
from libecalc.presentation.yaml.yaml_entities import MemoryResource
from libecalc.presentation.yaml.yaml_models.yaml_model import YamlValidator


class ResourceService(Protocol):
    """
    A service to get a resource
    """

    @abc.abstractmethod
    def get_resources(self, configuration: YamlValidator) -> dict[str, Resource]: ...


class DirectResourceService(ResourceService):
    def __init__(self, resources):
        self.resources = resources

    def get_resources(self, configuration: YamlValidator) -> dict[str, MemoryResource]:
        return self.resources
