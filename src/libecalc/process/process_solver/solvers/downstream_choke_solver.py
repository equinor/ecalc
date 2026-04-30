from collections.abc import Callable

from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.process_solver.configuration import ChokeConfiguration
from libecalc.process.process_solver.solver import Solution, Solver


class DownstreamChokeSolver(Solver[ChokeConfiguration]):
    def __init__(self, target_pressure: float):
        self._target_pressure = target_pressure

    def solve(self, func: Callable[[ChokeConfiguration], FluidStream]) -> Solution[ChokeConfiguration]:
        configuration = ChokeConfiguration(delta_pressure=0)
        outlet_stream = func(configuration)
        if outlet_stream.pressure_bara <= self._target_pressure:
            # Don't use choke if outlet pressure is below target
            return Solution(success=outlet_stream.pressure_bara == self._target_pressure, configuration=configuration)
        else:
            # Calculate needed pressure change in downstream choke
            pressure_change = outlet_stream.pressure_bara - self._target_pressure
            return Solution(success=True, configuration=ChokeConfiguration(delta_pressure=pressure_change))
