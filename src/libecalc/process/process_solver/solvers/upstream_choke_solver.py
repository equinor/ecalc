from collections.abc import Callable

from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.process_pipeline.process_error import RateTooHighError
from libecalc.process.process_solver.boundary import Boundary
from libecalc.process.process_solver.configuration import ChokeConfiguration
from libecalc.process.process_solver.search_strategies import RootFindingStrategy
from libecalc.process.process_solver.solver import Solution, Solver, SolverFailureStatus, TargetNotAchievableEvent


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
        def outlet_pressure(config: ChokeConfiguration) -> float:
            """Evaluate outlet pressure, treating RateTooHighError as infeasible (pressure = 0).

            A large upstream pressure drop drives suction pressure towards zero, causing actual
            volumetric flow to exceed the maximum rate the compressor chart can handle.
            When the process signals RateTooHighError the operating point is infeasible;
            returning 0 tells the solver that maximum choking brackets
            the target from below, so the algorithm converges in the feasible region.
            """
            try:
                return func(config).pressure_bara
            except RateTooHighError:
                return 0.0

        choke_configuration = ChokeConfiguration(delta_pressure=0)
        if outlet_pressure(choke_configuration) <= self._target_pressure:
            # Don't use choke if outlet pressure is below target
            return Solution(
                success=outlet_pressure(choke_configuration) == self._target_pressure,
                configuration=choke_configuration,
            )

        # Evaluate outlet pressure at maximum allowed upstream ΔP (within boundary).
        max_cfg = ChokeConfiguration(delta_pressure=self._delta_pressure_boundary.max)
        max_cfg_pressure = outlet_pressure(max_cfg)
        if max_cfg_pressure > self._target_pressure:
            # If we are still above target even at max choking, then no solution exists within the boundary.
            return Solution(
                success=False,
                configuration=max_cfg,
                failure_event=TargetNotAchievableEvent(
                    status=SolverFailureStatus.MINIMUM_ACHIEVABLE_DISCHARGE_PRESSURE_ABOVE_TARGET,
                    achievable_value=max_cfg_pressure,
                    target_value=self._target_pressure,
                ),
            )

        pressure_change = self._root_finding_strategy.find_root(
            boundary=self._delta_pressure_boundary,
            func=lambda x: outlet_pressure(ChokeConfiguration(delta_pressure=x)) - self._target_pressure,
        )

        return Solution(success=True, configuration=ChokeConfiguration(delta_pressure=pressure_change))
