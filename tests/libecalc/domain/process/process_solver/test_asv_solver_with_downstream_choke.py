import pytest

from libecalc.domain.process.entities.shaft import VariableSpeedShaft
from libecalc.domain.process.process_solver.asv_solvers import ASVSolver
from libecalc.domain.process.process_solver.boundary import Boundary
from libecalc.domain.process.process_solver.float_constraint import FloatConstraint
from libecalc.domain.process.process_system.compressor_stage_process_unit import CompressorStageProcessUnit
from libecalc.domain.process.process_system.process_unit import ProcessUnitId, create_process_unit_id
from libecalc.domain.process.value_objects.fluid_stream import FluidService, FluidStream


class SpeedCompressorStage(CompressorStageProcessUnit):
    """
    Test double that makes speed->pressure mapping deterministic:

      outlet_pressure = inlet_pressure + shaft_speed

    The capacity-related methods are implemented with wide limits to avoid
    interfering with tests that focus on solver orchestration.
    """

    def __init__(self, shaft: VariableSpeedShaft, fluid_service: FluidService):
        self._id = create_process_unit_id()
        self._shaft = shaft
        self._fluid_service = fluid_service

    def get_id(self) -> ProcessUnitId:
        return self._id

    def get_speed_boundary(self) -> Boundary:
        return Boundary(min=200.0, max=600.0)

    def get_maximum_standard_rate(self, inlet_stream: FluidStream) -> float:
        # "Infinite" capacity for test purposes
        return 1e30

    def get_minimum_standard_rate(self, inlet_stream: FluidStream) -> float:
        # "No minimum" for test purposes
        return 0.0

    def propagate_stream(self, inlet_stream: FluidStream) -> FluidStream:
        speed = self._shaft.get_speed()
        return self._fluid_service.create_stream_from_standard_rate(
            fluid_model=inlet_stream.fluid_model,
            pressure_bara=inlet_stream.pressure_bara + speed,
            standard_rate_m3_per_day=inlet_stream.standard_rate_sm3_per_day,
            temperature_kelvin=inlet_stream.temperature_kelvin,
        )


def test_asv_solver_applies_downstream_choke_when_speed_solution_is_at_min_speed(
    stream_factory,
    process_system_factory,
    fluid_service,
    choke_factory,
):
    """
    If the target outlet pressure is lower than the outlet pressure at minimum speed, SpeedSolver returns
    success=False and selects the minimum speed. ASVSolver should still attempt pressure control, and with a
    downstream choke it should be able to meet the target.
    """
    shaft = VariableSpeedShaft()
    downstream_choke = choke_factory()

    # One "compressor" stage that increases pressure with speed, followed by a downstream choke.
    compressor = SpeedCompressorStage(shaft=shaft, fluid_service=fluid_service)

    solver = ASVSolver(
        shaft=shaft,
        compressors=[compressor],
        fluid_service=fluid_service,
        individual_asv_control=False,
        downstream_choke=downstream_choke,
    )

    inlet_stream = stream_factory(standard_rate_m3_per_day=1000, pressure_bara=25.0)

    # At min speed=200 => baseline outlet = 25 + 200 = 225.
    # Choose a target lower than 225 so SpeedSolver returns min speed with success=False.
    target = FloatConstraint(50.0, abs_tol=1e-12)

    speed_solution, recirculation_solutions = solver.find_asv_solution(
        pressure_constraint=target,
        inlet_stream=inlet_stream,
    )

    # SpeedSolver could not meet the target pressure within the speed boundary,
    # so it returned the minimum speed as the best feasible speed.
    assert speed_solution.success is False
    assert speed_solution.configuration.speed == pytest.approx(200.0, abs=1e-12)

    # But overall solver should succeed via downstream choke pressure control.
    assert recirculation_solutions[0].success is True

    # Verify that downstream choking actually brings outlet down to target.
    # Build the same top-level process system that downstream choke runner uses:
    # recirc loops (1) + choke
    process_system = process_system_factory(process_units=[*solver.get_recirculation_loops(), downstream_choke])
    outlet = process_system.propagate_stream(inlet_stream=inlet_stream)

    assert outlet.pressure_bara == pytest.approx(target.value, abs=1e-12)
