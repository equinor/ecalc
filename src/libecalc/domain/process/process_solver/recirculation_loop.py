from libecalc.domain.process.entities.process_units.direct_mixer import DirectMixer
from libecalc.domain.process.entities.process_units.direct_splitter import DirectSplitter
from libecalc.domain.process.process_solver.configuration import (
    Configuration,
    ConfigurationHandlerId,
    RecirculationConfiguration,
)
from libecalc.domain.process.process_solver.configuration_handler import ConfigurationHandler


class RecirculationLoop(ConfigurationHandler):
    def __init__(
        self,
        configuration_handler_id: ConfigurationHandlerId,
        mixer: DirectMixer,
        splitter: DirectSplitter,
    ):
        self._id = configuration_handler_id
        self._mixer = mixer
        self._splitter = splitter

    def get_id(self) -> ConfigurationHandlerId:
        return self._id

    def set_recirculation_rate(self, rate: float):
        self._mixer.set_mix_rate(rate)
        self._splitter.set_split_rate(rate)

    def get_recirculation_rate(self) -> float:
        return self._mixer.get_mix_rate()

    def handle_configuration(self, configuration: Configuration):
        if configuration.configuration_handler_id != self._id:
            raise ValueError(
                f"Configuration with id '{configuration.configuration_handler_id}' cannot be applied to unit with id '{self._id}'"
            )

        assert isinstance(configuration.value, RecirculationConfiguration)
        self.set_recirculation_rate(configuration.value.recirculation_rate)
