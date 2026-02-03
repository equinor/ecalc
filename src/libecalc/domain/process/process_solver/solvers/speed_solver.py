import logging

from libecalc.domain.process.entities.shaft import Shaft
from libecalc.domain.process.process_solver.boundary import Boundary
from libecalc.domain.process.process_solver.search_strategies import RootFindingStrategy, SearchStrategy
from libecalc.domain.process.process_solver.solver import Solver
from libecalc.domain.process.process_system.process_error import ProcessError, RateTooHighError, RateTooLowError
from libecalc.domain.process.process_system.process_system import ProcessSystem
from libecalc.domain.process.value_objects.fluid_stream import FluidStream

logger = logging.getLogger(__name__)


class SpeedSolver(Solver):
    def __init__(
        self,
        search_strategy: SearchStrategy,
        root_finding_strategy: RootFindingStrategy,
        boundary: Boundary,
        target_pressure: float,
        shaft: Shaft,
    ):
        self._boundary = boundary
        self._target_pressure = target_pressure
        self._shaft = shaft
        self._search_strategy = search_strategy
        self._root_finding_strategy = root_finding_strategy

    def solve(
        self,
        process_system: ProcessSystem,
        inlet_stream: FluidStream,
    ) -> FluidStream | None:
        shaft = self._shaft

        def get_outlet_stream(speed: float) -> FluidStream:
            shaft.set_speed(speed)
            return process_system.propagate_stream(inlet_stream)

        try:
            maximum_speed_outlet_stream = get_outlet_stream(speed=self._boundary.max)
        except ProcessError as e:
            logger.debug(f"No solution found for maximum speed: {self._boundary.max}", exc_info=e)
            return None

        try:
            minimum_speed = self._boundary.min
            minimum_speed_outlet_stream = get_outlet_stream(speed=minimum_speed)
        except ProcessError as e:
            logger.debug(f"No solution found for minimum speed: {self._boundary.min}", exc_info=e)

            # rate is above maximum rate for minimum speed. Find the lowest minimum speed which gives a valid result
            def bool_speed_func(x):
                try:
                    get_outlet_stream(speed=x)
                    return False, True
                except RateTooHighError:
                    return True, False
                except RateTooLowError:
                    return False, False
                except ProcessError as e:
                    logger.debug(f"No solution found for speed: {x}", exc_info=e)
                    return False

            minimum_speed = self._search_strategy.search(
                boundary=self._boundary,
                func=bool_speed_func,
            )
            minimum_speed_outlet_stream = get_outlet_stream(speed=minimum_speed)

        if (
            minimum_speed_outlet_stream.pressure_bara
            <= self._target_pressure
            <= maximum_speed_outlet_stream.pressure_bara
        ):
            # Solution 1, iterate on speed until target discharge pressure is found
            def root_speed_func(x: float) -> float:
                # We should be able to produce an outlet stream since we adjust minimum speed above,
                # or exit if max speed is not enough
                out = get_outlet_stream(speed=x)
                return out.pressure_bara - self._target_pressure

            speed = self._root_finding_strategy.find_root(
                boundary=Boundary(min=minimum_speed, max=self._boundary.max),
                func=root_speed_func,
            )
            return get_outlet_stream(speed=speed)
        elif self._target_pressure < minimum_speed_outlet_stream.pressure_bara:
            # Solution 2, target pressure is too low
            shaft.set_speed(minimum_speed)
            return minimum_speed_outlet_stream

        # Solution 3, target discharge pressure is too high
        shaft.set_speed(self._boundary.max)
        return maximum_speed_outlet_stream
