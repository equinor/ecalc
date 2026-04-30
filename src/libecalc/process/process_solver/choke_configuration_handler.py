from typing import Final

from libecalc.process.process_solver.configuration import ChokeConfiguration, Configuration, ConfigurationHandlerId
from libecalc.process.process_solver.configuration_handler import ConfigurationHandler
from libecalc.process.process_units.choke import Choke


class ChokeConfigurationHandler(ConfigurationHandler):
    def __init__(self, choke: Choke, choke_configuration_handler_id: ConfigurationHandlerId | None = None):
        self._choke = choke
        self._id: Final[ConfigurationHandlerId] = choke_configuration_handler_id or ConfigurationHandler._create_id()

    def get_id(self) -> ConfigurationHandlerId:
        return self._id

    def handle_configuration(self, configuration: Configuration) -> None:
        assert configuration.configuration_handler_id == self._id, (
            f"Configuration id '{configuration.configuration_handler_id}' does not match choke configuration handler id '{self._id}'"
        )
        assert isinstance(configuration.value, ChokeConfiguration), (
            f"Expected configuration value to be of type 'ChokeConfiguration', got '{type(configuration.value)}'"
        )
        self._choke.set_pressure_change(configuration.value.delta_pressure)

    def reset(self) -> None:
        self._choke.set_pressure_change(0.0)
