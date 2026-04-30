import abc
from typing import Self

from libecalc.common.ddd.entity import Entity
from libecalc.common.utils.ecalc_uuid import ecalc_id_generator
from libecalc.process.process_solver.configuration import Configuration, ConfigurationHandlerId


class ConfigurationHandler(Entity[ConfigurationHandlerId], abc.ABC):
    @abc.abstractmethod
    def get_id(self) -> ConfigurationHandlerId: ...

    @abc.abstractmethod
    def handle_configuration(self, configuration: Configuration):
        """Handle the given configuration."""
        ...

    @abc.abstractmethod
    def reset(self) -> None:
        """Restore handler to its default/unconfigured state."""
        ...

    @classmethod
    def _create_id(cls: type[Self]) -> ConfigurationHandlerId:
        return ConfigurationHandlerId(ecalc_id_generator())
