from collections.abc import Iterable, Sequence

from libecalc.domain.process.process_pipeline.process_unit import ProcessUnit, ProcessUnitId
from libecalc.domain.process.process_solver.configuration import Configuration, ConfigurationHandlerId
from libecalc.domain.process.process_solver.configuration_handler import ConfigurationHandler
from libecalc.domain.process.process_solver.process_runner import ProcessRunner
from libecalc.domain.process.value_objects.fluid_stream import FluidStream


def propagate_stream_many(process_units: Sequence[ProcessUnit], inlet_stream: FluidStream) -> FluidStream:
    current_stream = inlet_stream
    for process_unit in process_units:
        current_stream = process_unit.propagate_stream(current_stream)
    return current_stream


class ProcessPipelineRunner(ProcessRunner):
    def __init__(self, configuration_handlers: Sequence[ConfigurationHandler], units: Sequence[ProcessUnit]):
        self._configuration_handlers = {handler.get_id(): handler for handler in configuration_handlers}
        self._units = {unit.get_id(): unit for unit in units}
        self._configurations: dict[ConfigurationHandlerId, Configuration] = {}

    @staticmethod
    def _apply_config_for_unit(configuration_handler: ConfigurationHandler, configuration: Configuration):
        configuration_handler.handle_configuration(configuration)

    def apply_configuration(self, configuration: Configuration):
        unit = self._get_configuration_handler(configuration.configuration_handler_id)
        self._configurations[configuration.configuration_handler_id] = configuration
        self._apply_config_for_unit(configuration_handler=unit, configuration=configuration)

    def _get_configuration_handler(self, configuration_handler_id: ConfigurationHandlerId) -> ConfigurationHandler:
        return self._configuration_handlers[configuration_handler_id]

    def _propagate_stream_to_id(
        self,
        inlet_stream: FluidStream,
        units: Iterable[ProcessUnit],
        to_id: ProcessUnitId,
    ) -> tuple[FluidStream, bool]:
        current_stream = inlet_stream
        for unit in units:
            if unit.get_id() == to_id:
                return current_stream, True
            current_stream = unit.propagate_stream(inlet_stream=current_stream)

        return current_stream, False

    def run(self, inlet_stream: FluidStream, to_id: ProcessUnitId | None = None) -> FluidStream:
        if to_id is not None:
            current_stream, found = self._propagate_stream_to_id(
                inlet_stream=inlet_stream, units=self._units.values(), to_id=to_id
            )
            assert found, f"Did not find unit with id '{to_id}'"
            return current_stream
        else:
            return propagate_stream_many(process_units=list(self._units.values()), inlet_stream=inlet_stream)
