from typing import Final

from libecalc.process.process_pipeline.process_unit import ProcessUnitId
from libecalc.process.process_solver.configuration import (
    Configuration,
    ConfigurationHandlerId,
    TemperatureSetterConfiguration,
)
from libecalc.process.process_solver.configuration_handler import ConfigurationHandler
from libecalc.process.process_units.temperature_setter import TemperatureSetter


class TemperatureSetterConfigurationHandler(ConfigurationHandler):
    def __init__(
        self, temperature_setter: TemperatureSetter, configuration_handler_id: ConfigurationHandlerId | None = None
    ):
        self._temperature_setter = temperature_setter
        self._id: Final[ConfigurationHandlerId] = configuration_handler_id or ConfigurationHandler._create_id()

    def get_id(self) -> ConfigurationHandlerId:
        return self._id

    def get_temperature_setter_id(self) -> ProcessUnitId:
        return self._temperature_setter.get_id()

    def handle_configuration(self, configuration: Configuration) -> None:
        assert configuration.configuration_handler_id == self._id, (
            f"Configuration id '{configuration.configuration_handler_id}' does not match configuration handler id '{self._id}'"
        )
        assert isinstance(configuration.value, TemperatureSetterConfiguration), (
            f"Expected configuration value to be of type '{TemperatureSetterConfiguration.__name__}', got '{type(configuration.value)}'"
        )
        self._temperature_setter.set_temperature(configuration.value.temperature)

    def reset(self) -> None:
        raise NotImplementedError("Calling reset on this should not happen, as it's shouldn't be manipulated by solver")
