from collections.abc import Callable

from libecalc.domain.process.process_solver.boundary import Boundary
from libecalc.domain.process.process_solver.search_strategies import RootFindingStrategy
from libecalc.domain.process.process_solver.solver import Solution, Solver
from libecalc.domain.process.value_objects.fluid_stream import FluidStream

from .downstream_choke_solver import ChokeConfiguration


class UpstreamChokeSolver(Solver):
    def __init__(
        self,
        root_finding_strategy: RootFindingStrategy,
        target_pressure: float,
        delta_pressure_boundary: Boundary,
    ):
        self._target_pressure = target_pressure
        self._delta_pressure_boundary = delta_pressure_boundary
        self._root_finding_strategy = root_finding_strategy

    def solve(self, func: Callable[[ChokeConfiguration], FluidStream]) -> Solution[ChokeConfiguration]:
        choke_configuration = ChokeConfiguration(delta_pressure=0)
        outlet_stream = func(choke_configuration)
        if outlet_stream.pressure_bara <= self._target_pressure:
            # Don't use choke if outlet pressure is below target
            return Solution(success=True, configuration=choke_configuration)

        pressure_change = self._root_finding_strategy.find_root(
            boundary=self._delta_pressure_boundary,
            func=lambda x: func(ChokeConfiguration(delta_pressure=x)).pressure_bara - self._target_pressure,
        )

        return Solution(success=True, configuration=ChokeConfiguration(delta_pressure=pressure_change))
