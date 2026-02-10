from libecalc.domain.process.entities.process_units.choke import Choke
from libecalc.domain.process.process_solver.boundary import Boundary
from libecalc.domain.process.process_solver.search_strategies import RootFindingStrategy
from libecalc.domain.process.process_solver.solver import Solver
from libecalc.domain.process.process_system.process_system import ProcessSystem
from libecalc.domain.process.value_objects.fluid_stream import FluidStream


class UpstreamChokeSolver(Solver):
    def __init__(
        self,
        root_finding_strategy: RootFindingStrategy,
        target_pressure: float,
        delta_pressure_boundary: Boundary,
        choke: Choke,
    ):
        self._target_pressure = target_pressure
        self._delta_pressure_boundary = delta_pressure_boundary
        self._choke = choke
        self._root_finding_strategy = root_finding_strategy

    def solve(self, process_system: ProcessSystem, inlet_stream: FluidStream) -> FluidStream | None:
        outlet_stream = process_system.propagate_stream(inlet_stream)
        if outlet_stream.pressure_bara <= self._target_pressure:
            # Don't use choke if outlet pressure is below target
            return outlet_stream

        def get_outlet_stream(delta_pressure: float) -> FluidStream:
            self._choke.set_pressure_change(delta_pressure)
            return process_system.propagate_stream(inlet_stream=inlet_stream)

        pressure_change = self._root_finding_strategy.find_root(
            boundary=self._delta_pressure_boundary,
            func=lambda x: get_outlet_stream(delta_pressure=x).pressure_bara - self._target_pressure,
        )

        return get_outlet_stream(pressure_change)
