from typing import Final

from libecalc.process.process_pipeline.process_unit import ProcessUnitId
from libecalc.process.process_solver.configuration import (
    Configuration,
    ConfigurationHandlerId,
    RecirculationConfiguration,
)
from libecalc.process.process_solver.configuration_handler import ConfigurationHandler
from libecalc.process.pump.process_units.liquid_direct_mixer import LiquidDirectMixer
from libecalc.process.pump.process_units.liquid_direct_splitter import LiquidDirectSplitter


class LiquidRecirculationLoop(ConfigurationHandler):
    """Minimum-flow recirculation from the splitter back to the mixer.

    It sets the same rate [m3/h] on the mixer and the splitter, so the pump between them runs at the
    recirculated rate on top of the rate that continues downstream. Like the gas recirculation loop it
    is its own concept with its own identity, not a serial connection.
    """

    def __init__(
        self,
        mixer: LiquidDirectMixer,
        splitter: LiquidDirectSplitter,
        configuration_handler_id: ConfigurationHandlerId | None = None,
    ):
        self._id: Final[ConfigurationHandlerId] = configuration_handler_id or ConfigurationHandler._create_id()
        self._mixer = mixer
        self._splitter = splitter

    def get_id(self) -> ConfigurationHandlerId:
        return self._id

    def get_mixer_process_unit_id(self) -> ProcessUnitId:
        return self._mixer.get_id()

    def set_recirculation_rate_m3_per_hour(self, recirculation_rate_m3_per_hour: float) -> None:
        self._mixer.set_mix_rate_m3_per_hour(recirculation_rate_m3_per_hour)
        self._splitter.set_split_rate_m3_per_hour(recirculation_rate_m3_per_hour)

    def handle_configuration(self, configuration: Configuration) -> None:
        if configuration.configuration_handler_id != self._id:
            raise ValueError(
                f"Configuration with id '{configuration.configuration_handler_id}' cannot be applied to the recirculation loop with id '{self._id}'"
            )
        if not isinstance(configuration.value, RecirculationConfiguration):
            raise ValueError(
                f"Expected a RecirculationConfiguration for the recirculation loop, got '{type(configuration.value)}'"
            )
        self.set_recirculation_rate_m3_per_hour(configuration.value.recirculation_rate)

    def reset(self) -> None:
        self.set_recirculation_rate_m3_per_hour(0.0)
