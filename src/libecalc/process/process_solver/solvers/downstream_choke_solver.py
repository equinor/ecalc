from libecalc.process.process_pipeline.propagation_failure import PropagationFailure
from libecalc.process.process_solver.configuration import ChokeConfiguration
from libecalc.process.process_solver.solver import PropagationCallback, Solution, Solver


class DownstreamChokeSolver(Solver[ChokeConfiguration]):
    def __init__(self, target_pressure: float):
        self._target_pressure = target_pressure

    def solve(self, func: PropagationCallback[ChokeConfiguration]) -> Solution[ChokeConfiguration]:
        configuration = ChokeConfiguration(delta_pressure=0)
        outlet = func(configuration)
        if isinstance(outlet, PropagationFailure):
            return Solution.failed(configuration=configuration, failure=outlet)
        if outlet.pressure_bara <= self._target_pressure:
            # Don't use choke if outlet pressure is below target
            return Solution(success=outlet.pressure_bara == self._target_pressure, configuration=configuration)
        else:
            # Calculate needed pressure change in downstream choke
            pressure_change = outlet.pressure_bara - self._target_pressure
            return Solution(success=True, configuration=ChokeConfiguration(delta_pressure=pressure_change))
