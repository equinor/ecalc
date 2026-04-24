import abc
from typing import NewType
from uuid import UUID

from libecalc.common.ddd.entity import Entity
from libecalc.common.utils.ecalc_uuid import ecalc_id_generator
from libecalc.domain.process.process_solver.configuration import Configuration

ConfigurationHandlerId = NewType("ConfigurationHandlerId", UUID)


class ConfigurationHandler(Entity[ConfigurationHandlerId], abc.ABC):
    @abc.abstractmethod
    def get_id(self) -> ConfigurationHandlerId: ...

    @abc.abstractmethod
    def handle_configuration(self, configuration: Configuration):
        """Handle the given configuration."""
        ...

    @staticmethod
    def _create_id() -> ConfigurationHandlerId:
        return ConfigurationHandlerId(ecalc_id_generator())
