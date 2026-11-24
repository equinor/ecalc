from typing import Final

from libecalc.process.process_solver.configuration import ChokeConfiguration, Configuration, ConfigurationHandlerId
from libecalc.process.process_solver.configuration_handler import ConfigurationHandler
from libecalc.process.pump.process_units.liquid_choke import LiquidChoke


class LiquidChokeConfigurationHandler(ConfigurationHandler):
    def __init__(self, choke: LiquidChoke, configuration_handler_id: ConfigurationHandlerId | None = None):
        self._id: Final[ConfigurationHandlerId] = configuration_handler_id or ConfigurationHandler._create_id()
        self._choke = choke

    def get_id(self) -> ConfigurationHandlerId:
        return self._id

    def handle_configuration(self, configuration: Configuration) -> None:
        if configuration.configuration_handler_id != self._id:
            raise ValueError(
                f"Configuration with id '{configuration.configuration_handler_id}' cannot be applied to the choke configuration handler with id '{self._id}'"
            )
        if not isinstance(configuration.value, ChokeConfiguration):
            raise ValueError(
                f"Expected a ChokeConfiguration for the choke configuration handler, got '{type(configuration.value)}'"
            )
        self._choke.set_pressure_drop_bara(configuration.value.delta_pressure)

    def reset(self) -> None:
        self._choke.set_pressure_drop_bara(0.0)
