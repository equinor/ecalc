from libecalc.domain.process.compressor.core.train.utils.numeric_methods import find_root
from libecalc.domain.process.process_solver.solver import Solver
from libecalc.domain.process.process_system.process_system import ProcessSystem
from libecalc.domain.process.value_objects.fluid_stream import FluidService, FluidStream


class UpstreamChokeSolver(Solver):
    def __init__(self, target_pressure: float, fluid_service: FluidService, minimum_pressure: float):
        self._target_pressure = target_pressure
        self._fluid_service = fluid_service
        self._minimum_pressure = minimum_pressure

    def solve(self, process_system: ProcessSystem, inlet_stream: FluidStream) -> FluidStream | None:
        upstream_choke = process_system.get_upstream_choke()
        assert upstream_choke is not None, "UpstreamChokeSolver needs an upstream choke"

        outlet_stream = process_system.propagate_stream(inlet_stream)
        if outlet_stream.pressure_bara <= self._target_pressure:
            # Don't use choke if outlet pressure is below target
            return outlet_stream

        def get_outlet_pressure(inlet_pressure: float) -> float:
            choked_inlet_stream = self._fluid_service.create_stream_from_standard_rate(
                fluid_model=inlet_stream.fluid_model,
                pressure_bara=inlet_pressure,
                temperature_kelvin=inlet_stream.pressure_bara,
                standard_rate_m3_per_day=inlet_stream.standard_rate_sm3_per_day,
            )
            outlet_stream = process_system.propagate_stream(inlet_stream=choked_inlet_stream)
            return outlet_stream.pressure_bara

        choked_inlet_pressure = find_root(
            lower_bound=self._minimum_pressure,
            upper_bound=inlet_stream.pressure_bara,
            func=lambda x: get_outlet_pressure(inlet_pressure=x) - self._target_pressure,
        )

        pressure_change = inlet_stream.pressure_bara - choked_inlet_pressure
        upstream_choke.set_pressure_change(pressure_change=pressure_change)
        return process_system.propagate_stream(inlet_stream=inlet_stream)
