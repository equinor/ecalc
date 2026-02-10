from collections.abc import Callable
from dataclasses import dataclass

from libecalc.domain.process.process_solver.solver import Solution, Solver
from libecalc.domain.process.value_objects.fluid_stream import FluidStream


@dataclass
class ChokeConfiguration:
    delta_pressure: float


class DownstreamChokeSolver(Solver[ChokeConfiguration]):
    def __init__(self, target_pressure: float):
        self._target_pressure = target_pressure

    def solve(self, func: Callable[[ChokeConfiguration], FluidStream]) -> Solution[ChokeConfiguration]:
        configuration = ChokeConfiguration(delta_pressure=0)
        outlet_stream = func(configuration)
        if outlet_stream.pressure_bara <= self._target_pressure:
            # Don't use choke if outlet pressure is below target
            return Solution(success=True, configuration=configuration)
        else:
            # Calculate needed pressure change in downstream choke
            pressure_change = outlet_stream.pressure_bara - self._target_pressure
            return Solution(success=True, configuration=ChokeConfiguration(delta_pressure=pressure_change))
