from libecalc.domain.process.process_solver.solver import Solver
from libecalc.domain.process.process_system.process_system import ProcessSystem
from libecalc.domain.process.value_objects.fluid_stream import FluidStream


class DownstreamChokeSolver(Solver):
    def __init__(self, target_pressure: float):
        self._target_pressure = target_pressure

    def solve(self, process_system: ProcessSystem, inlet_stream: FluidStream) -> FluidStream | None:
        downstream_choke = process_system.get_downstream_choke()
        assert downstream_choke is not None, "DownstreamChokeSolver needs a downstream choke"

        outlet_stream = process_system.propagate_stream(inlet_stream=inlet_stream)
        if outlet_stream.pressure_bara <= self._target_pressure:
            # Don't use choke if outlet pressure is below target
            return outlet_stream
        else:
            # Calculate needed pressure change in downstream choke
            pressure_change = outlet_stream.pressure_bara - self._target_pressure
            downstream_choke.set_pressure_change(pressure_change=pressure_change)
            return process_system.propagate_stream(inlet_stream=inlet_stream)
