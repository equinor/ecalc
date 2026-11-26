from collections.abc import Mapping, Sequence

from libecalc.process.process_pipeline.process_unit import ProcessUnitId
from libecalc.process.process_solver.configuration import (
    Configuration,
    ConfigurationHandlerId,
    OperatingConfiguration,
)
from libecalc.process.process_solver.configuration_handler import ConfigurationHandler
from libecalc.process.pump.liquid_stream import LiquidStream
from libecalc.process.pump.process_units.liquid_process_unit import LiquidProcessUnit


class LiquidProcessPipelineRunner:
    def __init__(
        self,
        configuration_handlers: Sequence[ConfigurationHandler],
        units: Sequence[LiquidProcessUnit],
    ):
        self._configuration_handlers = {handler.get_id(): handler for handler in configuration_handlers}
        if len(self._configuration_handlers) != len(configuration_handlers):
            raise ValueError("A configuration handler id occurs more than once in the pipeline.")
        self._units = tuple(units)
        if len({unit.get_id() for unit in self._units}) != len(self._units):
            raise ValueError("A process unit id occurs more than once in the pipeline.")

    def apply_configuration(self, configuration: Configuration[OperatingConfiguration]) -> None:
        self._get_configuration_handler(configuration.configuration_handler_id).handle_configuration(configuration)

    def apply_configurations(self, configurations: Sequence[Configuration[OperatingConfiguration]]) -> None:
        for configuration in configurations:
            self.apply_configuration(configuration)

    def run(self, inlet_stream: LiquidStream, to_id: ProcessUnitId | None = None) -> LiquidStream:
        """The stream that enters the unit ``to_id``, or the stream out of the last unit when no id is given."""
        stream = inlet_stream
        for unit in self._units:
            if unit.get_id() == to_id:
                return stream
            stream = unit.propagate_stream(stream)
        if to_id is not None:
            raise ValueError(f"No process unit with id '{to_id}' in the pipeline.")
        return stream

    def run_to_each_unit(self, inlet_stream: LiquidStream) -> Mapping[ProcessUnitId, LiquidStream]:
        """The stream that enters each unit, by the unit's id, from one run through the pipeline."""
        streams: dict[ProcessUnitId, LiquidStream] = {}
        stream = inlet_stream
        for unit in self._units:
            streams[unit.get_id()] = stream
            stream = unit.propagate_stream(stream)
        return streams

    def _get_configuration_handler(self, handler_id: ConfigurationHandlerId) -> ConfigurationHandler:
        handler = self._configuration_handlers.get(handler_id)
        if handler is None:
            raise ValueError(f"No configuration handler with id '{handler_id}' in the pipeline.")
        return handler
