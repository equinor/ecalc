from libecalc.domain.process.compressor.core.train.utils.numeric_methods import find_root
from libecalc.domain.process.process_solver.boundary import Boundary
from libecalc.domain.process.process_solver.solver import Solver
from libecalc.domain.process.process_system.process_system import ProcessSystem
from libecalc.domain.process.value_objects.fluid_stream import FluidService, FluidStream


class UpstreamChokeSolver(Solver):
    def __init__(self, outlet_pressure: float, fluid_service: FluidService, inlet_pressure_boundary: Boundary):
        self._outlet_pressure = outlet_pressure
        self._fluid_service = fluid_service
        self._inlet_pressure_boundary = inlet_pressure_boundary

    def solve(self, process_system: ProcessSystem, inlet_stream: FluidStream) -> FluidStream | None:
        upstream_choke = process_system.get_upstream_choke()
        assert upstream_choke is not None, "UpstreamChokeSolver needs an upstream choke"

        def get_outlet_pressure(inlet_pressure: float) -> float:
            choked_inlet_stream = self._fluid_service.create_stream_from_standard_rate(
                fluid_model=inlet_stream.fluid_model,
                pressure_bara=inlet_pressure,
                temperature_kelvin=inlet_stream.pressure_bara,
                standard_rate_m3_per_day=inlet_stream.standard_rate_sm3_per_day,
            )
            outlet_stream = process_system.propagate_stream(inlet_stream=choked_inlet_stream)
            assert outlet_stream is not None, "Unable to produce an outlet stream"
            return outlet_stream.pressure_bara

        choked_inlet_pressure = find_root(
            lower_bound=self._inlet_pressure_boundary.min,
            upper_bound=self._inlet_pressure_boundary.max,
            func=lambda x: get_outlet_pressure(inlet_pressure=x) - self._outlet_pressure,
        )

        upstream_choke.set_target_pressure(choked_inlet_pressure)

        return process_system.propagate_stream(inlet_stream=inlet_stream)
