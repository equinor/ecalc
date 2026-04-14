from collections.abc import Iterable, Sequence

from libecalc.domain.component_validation_error import DomainValidationException
from libecalc.domain.process.entities.process_units.choke import Choke
from libecalc.domain.process.entities.process_units.pressure_ratio_compressor import PressureRatioCompressor
from libecalc.domain.process.entities.process_units.recirculation_loop import RecirculationLoop
from libecalc.domain.process.entities.shaft import Shaft
from libecalc.domain.process.entities.shaft.shaft import ShaftId
from libecalc.domain.process.process_solver.configuration import Configuration, SimulationUnitId
from libecalc.domain.process.process_solver.process_runner import ProcessRunner
from libecalc.domain.process.process_solver.solvers.downstream_choke_solver import ChokeConfiguration
from libecalc.domain.process.process_solver.solvers.recirculation_solver import RecirculationConfiguration
from libecalc.domain.process.process_solver.solvers.speed_solver import SpeedConfiguration
from libecalc.domain.process.process_system.process_system import ProcessSystem, ProcessSystemId
from libecalc.domain.process.process_system.process_unit import ProcessUnit, ProcessUnitId
from libecalc.domain.process.value_objects.fluid_stream import FluidStream


class ProcessSystemRunner(ProcessRunner):
    def __init__(self, shaft: Shaft, units: Sequence[ProcessUnit | ProcessSystem]):
        for unit in units:
            if isinstance(unit, PressureRatioCompressor):
                raise DomainValidationException(
                    "ProcessSystemRunner (speed-based) cannot contain PressureRatioCompressor units. "
                    "Use CommonPressureRatioSolver instead."
                )
        self._shaft = shaft
        self._units = {unit.get_id(): unit for unit in units}
        self._configurations: dict[ProcessUnitId | ProcessSystemId | ShaftId, Configuration] = {}

    @staticmethod
    def _apply_config_for_unit(unit: ProcessUnit | ProcessSystem | Shaft, configuration: Configuration):
        if isinstance(unit, RecirculationLoop):
            assert isinstance(configuration.value, RecirculationConfiguration)
            unit.set_recirculation_rate(configuration.value.recirculation_rate)
            return
        elif isinstance(unit, Choke):
            assert isinstance(configuration.value, ChokeConfiguration)
            unit.set_pressure_change(configuration.value.delta_pressure)
            return
        elif isinstance(unit, Shaft):
            assert isinstance(configuration.value, SpeedConfiguration)
            unit.set_speed(configuration.value.speed)
        else:
            raise ValueError(f"Unhandled unit '{type(unit)}' with id '{configuration.simulation_unit_id}'")

    @staticmethod
    def _validate_config_for_unit(unit: ProcessUnit | ProcessSystem | Shaft, configuration: Configuration):
        if isinstance(unit, RecirculationLoop):
            return isinstance(configuration.value, RecirculationConfiguration)
        elif isinstance(unit, Choke):
            return isinstance(configuration.value, ChokeConfiguration)
        elif isinstance(unit, Shaft):
            return isinstance(configuration.value, SpeedConfiguration)
        else:
            return False

    def apply_configuration(self, configuration: Configuration):
        unit = self._get_unit(configuration.simulation_unit_id)
        assert self._validate_config_for_unit(
            unit, configuration
        ), f"Invalid configuration {type(configuration.value)} for unit '{type(unit)}'"
        self._configurations[configuration.simulation_unit_id] = configuration
        self._apply_config_for_unit(unit=unit, configuration=configuration)

    def _get_unit(self, unit_id: SimulationUnitId) -> ProcessUnit | ProcessSystem | Shaft:
        unit = None
        if self._shaft.get_id() == unit_id:
            unit = self._shaft

        if unit is None:
            unit = self._units.get(unit_id)  # type: ignore[arg-type]

        if unit is None:
            raise ValueError(f"Unit with id '{unit_id}' does not exist.")
        return unit

    def _propagate_stream_to_id(
        self,
        inlet_stream: FluidStream,
        units: Iterable[ProcessUnit | ProcessSystem],
        to_id: SimulationUnitId,
    ) -> tuple[FluidStream, bool]:
        current_stream = inlet_stream
        for unit in units:
            if unit.get_id() == to_id:
                return current_stream, True

            if isinstance(unit, ProcessSystem):
                current_stream, found = self._propagate_stream_to_id(
                    inlet_stream=current_stream, units=unit.get_process_units(), to_id=to_id
                )
                if found:
                    return current_stream, found

            elif isinstance(unit, ProcessUnit):
                current_stream = unit.propagate_stream(inlet_stream=current_stream)

            else:
                raise ValueError("Unhandled unit type '{type(unit)}' with id '{unit.get_id()}'")

        return current_stream, False

    def run(self, inlet_stream: FluidStream, to_id: SimulationUnitId | None = None) -> FluidStream:
        if to_id is not None:
            current_stream, found = self._propagate_stream_to_id(
                inlet_stream=inlet_stream, units=self._units.values(), to_id=to_id
            )
            assert found, f"Did not find unit with id '{to_id}'"
            return current_stream
        else:
            current_stream = inlet_stream
            for unit in self._units.values():
                current_stream = unit.propagate_stream(current_stream)

            return current_stream
