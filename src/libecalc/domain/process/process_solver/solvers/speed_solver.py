from libecalc.domain.process.compressor.core.train.utils.numeric_methods import (
    find_root,
    maximize_x_given_boolean_condition_function,
)
from libecalc.domain.process.process_solver.boundary import Boundary
from libecalc.domain.process.process_solver.solver import Solver
from libecalc.domain.process.process_system.process_system import ProcessSystem
from libecalc.domain.process.value_objects.fluid_stream import FluidStream


class SpeedSolver(Solver):
    def __init__(self, boundary: Boundary, target_pressure: float):
        self._boundary = boundary
        self._target_pressure = target_pressure

    def solve(
        self,
        process_system: ProcessSystem,
        inlet_stream: FluidStream,
    ) -> FluidStream | None:
        shaft = process_system.get_shaft()

        def get_outlet_stream(speed: float) -> FluidStream | None:
            shaft.set_speed(speed)
            return process_system.propagate_stream(inlet_stream)

        maximum_speed = self._boundary.max
        maximum_speed_outlet_stream = get_outlet_stream(speed=maximum_speed)
        if maximum_speed_outlet_stream is None:
            # Outside capacity
            return maximum_speed_outlet_stream

        minimum_speed = self._boundary.min
        minimum_speed_outlet_stream = get_outlet_stream(speed=minimum_speed)
        if minimum_speed_outlet_stream is None:
            # rate is above maximum rate for minimum speed. Find the lowest minimum speed which gives a valid result
            minimum_speed = -maximize_x_given_boolean_condition_function(
                x_min=-maximum_speed,
                x_max=-minimum_speed,
                bool_func=lambda x: get_outlet_stream(speed=x) is not None,
            )
            minimum_speed_outlet_stream = get_outlet_stream(speed=minimum_speed)

        if (
            minimum_speed_outlet_stream.pressure_bara
            <= self._target_pressure
            <= maximum_speed_outlet_stream.pressure_bara
        ):
            # Solution 1, iterate on speed until target discharge pressure is found
            def f(speed: float) -> float:
                out = get_outlet_stream(speed=speed)
                # We should be able to produce an outlet stream since we adjust minimum speed above,
                # or exit if max speed is not enough
                assert out is not None, "Unable to produce an outlet stream"
                return out.pressure_bara - self._target_pressure

            speed = find_root(
                lower_bound=minimum_speed,
                upper_bound=maximum_speed,
                func=f,
            )
            return get_outlet_stream(speed=speed)
        elif self._target_pressure < minimum_speed_outlet_stream.pressure_bara:
            # Solution 2, target pressure is too low
            shaft.set_speed(minimum_speed)
            return minimum_speed_outlet_stream

        # Solution 3, target discharge pressure is too high
        shaft.set_speed(maximum_speed)
        return maximum_speed_outlet_stream
