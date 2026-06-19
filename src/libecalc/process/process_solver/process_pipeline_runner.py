from collections.abc import Iterable, Sequence

from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.process_pipeline.process_unit import ProcessUnit, ProcessUnitId
from libecalc.process.process_solver import solver_debug
from libecalc.process.process_solver.configuration import Configuration, ConfigurationHandlerId
from libecalc.process.process_solver.configuration_handler import ConfigurationHandler
from libecalc.process.process_solver.process_runner import ProcessRunner


def propagate_stream_many(process_units: Sequence[ProcessUnit], inlet_stream: FluidStream) -> FluidStream:
    current_stream = inlet_stream
    debug = solver_debug.is_enabled()
    for process_unit in process_units:
        if debug:
            solver_debug.emit(
                "unit.enter",
                unit_id=str(process_unit.get_id()),
                unit_type=process_unit.__class__.__name__,
                inlet_pressure=current_stream.pressure_bara,
                inlet_rate=current_stream.standard_rate_sm3_per_day,
                inlet_actual_rate_m3h=current_stream.volumetric_rate_m3_per_hour,
                inlet_temperature_celsius=current_stream.temperature_kelvin - 273.15,
            )
        current_stream = process_unit.propagate_stream(current_stream)
        if debug:
            solver_debug.emit(
                "unit.exit",
                unit_id=str(process_unit.get_id()),
                unit_type=process_unit.__class__.__name__,
                outlet_pressure=current_stream.pressure_bara,
                outlet_rate=current_stream.standard_rate_sm3_per_day,
                outlet_actual_rate_m3h=current_stream.volumetric_rate_m3_per_hour,
                outlet_temperature_celsius=current_stream.temperature_kelvin - 273.15,
            )
    return current_stream


class ProcessPipelineRunner(ProcessRunner):
    def __init__(self, configuration_handlers: Sequence[ConfigurationHandler], units: Sequence[ProcessUnit]):
        self._configuration_handlers = {handler.get_id(): handler for handler in configuration_handlers}
        self._units = {unit.get_id(): unit for unit in units}
        print(f"order of units: {self._units}")

    @staticmethod
    def _apply_config_for_unit(configuration_handler: ConfigurationHandler, configuration: Configuration):
        configuration_handler.handle_configuration(configuration)

    def apply_configuration(self, configuration: Configuration):
        unit = self._get_configuration_handler(configuration.configuration_handler_id)
        self._apply_config_for_unit(configuration_handler=unit, configuration=configuration)

    def reset_configuration_handler(self, handler_id: ConfigurationHandlerId) -> None:
        self._get_configuration_handler(handler_id).reset()

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
