from libecalc.domain.process.entities.process_units.choke import Choke
from libecalc.domain.process.process_solver.configuration import (
    ChokeConfiguration,
    Configuration,
)
from libecalc.domain.process.process_solver.configuration_handler import (
    ConfigurationHandler,
    ConfigurationHandlerId,
)


class ChokeConfigurationHandler(ConfigurationHandler):
    def __init__(
        self, choke: Choke, choke_configuration_handler_id: ConfigurationHandlerId = ConfigurationHandler._create_id()
    ):
        self._id = choke_configuration_handler_id
        self._choke = choke

    def get_id(self) -> ConfigurationHandlerId:
        return self._id

    def handle_configuration(self, configuration: Configuration) -> None:
        assert (
            configuration.configuration_handler_id == self._id
        ), f"Configuration id '{configuration.configuration_handler_id}' does not match choke configuration handler id '{self._id}'"
        assert isinstance(
            configuration.value, ChokeConfiguration
        ), f"Expected configuration value to be of type 'ChokeConfiguration', got '{type(configuration.value)}'"
        self._choke.set_pressure_change(configuration.value.delta_pressure)
