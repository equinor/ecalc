from collections.abc import Callable
from typing import Literal

from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.process_pipeline.process_error import RateTooHighError, RateTooLowError
from libecalc.process.process_solver.boundary import Boundary
from libecalc.process.process_solver.configuration import RecirculationConfiguration
from libecalc.process.process_solver.finder import Finder, Finding
from libecalc.process.process_solver.float_constraint import FloatConstraint
from libecalc.process.process_solver.search_strategies import Bisect, BisectResult, RootFindingStrategy
from libecalc.process.process_solver.solver import RateTooHighFailure, TargetDirection, TargetPressureUnreachableFailure


class RecirculationLoopRateFinder(Finder):
    def __init__(
        self,
        search_strategy: Bisect,
        root_finding_strategy: RootFindingStrategy,
        recirculation_rate_boundary: Boundary,
        target_pressure: FloatConstraint | None = None,
    ):
        self._recirculation_rate_boundary = recirculation_rate_boundary
        self._target_pressure = target_pressure
        self._search_strategy = search_strategy
        self._root_finding_strategy = root_finding_strategy

    def find(self, func: Callable[[RecirculationConfiguration], FluidStream]) -> Finding[RecirculationConfiguration]:
        try:
            minimum_rate = self._find_min_within_capacity_rate(func)
        except RateTooHighError as e:
            # Flow is above stonewall at zero recirculation; adding recirculation cannot help.
            return Finding(
                configuration=RecirculationConfiguration(recirculation_rate=self._recirculation_rate_boundary.min),
                failure=RateTooHighFailure.from_error(e),
            )

        target_pressure = self._target_pressure
        if target_pressure is None:
            # Recirc used to get within capacity, but not to meet constraints
            return Finding(configuration=RecirculationConfiguration(recirculation_rate=minimum_rate))

        maximum_rate = self._find_max_within_capacity_rate(func)

        minimum_outlet_stream = func(RecirculationConfiguration(recirculation_rate=minimum_rate))
        # Highest possible pressure is too low
        if minimum_outlet_stream.pressure_bara < target_pressure:
            return Finding(
                configuration=RecirculationConfiguration(recirculation_rate=minimum_rate),
                failure=TargetPressureUnreachableFailure(
                    achievable_pressure_bara=minimum_outlet_stream.pressure_bara,
                    target_pressure_bara=target_pressure.value,
                    direction=TargetDirection.MAX_BELOW_TARGET,
                ),
            )
        if minimum_outlet_stream.pressure_bara == target_pressure:
            return Finding(configuration=RecirculationConfiguration(recirculation_rate=minimum_rate))

        maximum_outlet_stream = func(RecirculationConfiguration(recirculation_rate=maximum_rate))
        if maximum_outlet_stream.pressure_bara == target_pressure:
            return Finding(configuration=RecirculationConfiguration(recirculation_rate=maximum_rate))
        # Lowest possible pressure is too high
        if maximum_outlet_stream.pressure_bara > target_pressure:
            return Finding(
                configuration=RecirculationConfiguration(recirculation_rate=maximum_rate),
                failure=TargetPressureUnreachableFailure(
                    achievable_pressure_bara=maximum_outlet_stream.pressure_bara,
                    target_pressure_bara=target_pressure.value,
                    direction=TargetDirection.MIN_ABOVE_TARGET,
                ),
            )

        recirculation_rate = self._root_finding_strategy.find_root(
            boundary=Boundary(min=minimum_rate, max=maximum_rate),
            func=lambda x: func(RecirculationConfiguration(recirculation_rate=x)).pressure_bara - target_pressure.value,
        )
        return Finding(configuration=RecirculationConfiguration(recirculation_rate=recirculation_rate))

    def _find_min_within_capacity_rate(self, func: Callable[[RecirculationConfiguration], FluidStream]) -> float:
        """Return the smallest recirculation rate within flow capacity.

        ``RateTooLow`` at the boundary minimum is recoverable (more recirculation adds
        flow); ``RateTooHigh`` is not and propagates to the caller.
        """
        minimum_rate = self._recirculation_rate_boundary.min
        try:
            func(RecirculationConfiguration(recirculation_rate=minimum_rate))
            return minimum_rate
        except RateTooLowError:
            return self._search_strategy.search(
                boundary=self._recirculation_rate_boundary,
                func=lambda x: self._bool_func(func, x, mode="minimize"),
            )

    def _find_max_within_capacity_rate(self, func: Callable[[RecirculationConfiguration], FluidStream]) -> float:
        """Return the largest recirculation rate within flow capacity.

        ``RateTooHigh`` at the boundary maximum is recoverable: search downward.
        """
        maximum_rate = self._recirculation_rate_boundary.max
        try:
            func(RecirculationConfiguration(recirculation_rate=maximum_rate))
            return maximum_rate
        except RateTooHighError:
            return self._search_strategy.search(
                boundary=self._recirculation_rate_boundary,
                func=lambda x: self._bool_func(func, x, mode="maximize"),
            )

    @staticmethod
    def _bool_func(
        func: Callable[[RecirculationConfiguration], FluidStream],
        x: float,
        mode: Literal["minimize", "maximize"],
    ) -> BisectResult:
        """Probe a candidate rate for the search strategy.

        Returns a ``BisectResult`` where the two booleans are decoupled so an
        out-of-capacity candidate can never be accepted as a solution.
        """
        try:
            func(RecirculationConfiguration(recirculation_rate=x))
            return BisectResult(higher=mode != "minimize", accepted=True)
        except RateTooLowError:
            return BisectResult(higher=True, accepted=False)
        except RateTooHighError:
            return BisectResult(higher=False, accepted=False)
