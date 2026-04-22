import abc

from libecalc.domain.process.process_solver.configuration import Configuration, ConfigurationHandlerId


class ConfigurationHandler(abc.ABC):
    @abc.abstractmethod
    def get_id(self) -> ConfigurationHandlerId: ...

    @abc.abstractmethod
    def handle_configuration(self, configuration: Configuration):
        """Handle the given configuration."""
        ...
