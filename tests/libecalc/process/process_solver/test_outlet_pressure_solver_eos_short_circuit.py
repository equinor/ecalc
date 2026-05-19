from unittest.mock import MagicMock, patch
from uuid import uuid4

from libecalc.process.process_pipeline.process_error import CompressorOperatingPoint
from libecalc.process.process_pipeline.process_unit import ProcessUnitId
from libecalc.process.process_solver.configuration import ConfigurationHandlerId, SpeedConfiguration
from libecalc.process.process_solver.float_constraint import FloatConstraint
from libecalc.process.process_solver.outlet_pressure_solver import OutletPressureSolver
from libecalc.process.process_solver.solver import (
    OutletFluidNotAchievableFailure,
    Solution,
)


def test_find_solution_short_circuits_on_outlet_fluid_not_achievable():
    eos_failure = OutletFluidNotAchievableFailure(
        source_id=ProcessUnitId(uuid4()),
        unachievable_operating_point=CompressorOperatingPoint(
            inlet_pressure_bara=10.0,
            inlet_temperature_kelvin=300.0,
            actual_rate_m3_per_hour=0.0,
            polytropic_head_joule_per_kg=0.0,
            polytropic_efficiency=0.0,
            speed=600.0,
        ),
    )
    speed_solution = Solution(
        success=False,
        configuration=SpeedConfiguration(speed=600.0),
        failure=eos_failure,
    )

    pressure_control_strategy = MagicMock()
    anti_surge_strategy = MagicMock()
    runner = MagicMock()
    solver = OutletPressureSolver(
        shaft_id=ConfigurationHandlerId(uuid4()),
        process_pipeline_id=MagicMock(),
        runner=runner,
        anti_surge_strategy=anti_surge_strategy,
        pressure_control_strategy=pressure_control_strategy,
        root_finding_strategy=MagicMock(),
        speed_boundary=MagicMock(),
    )

    with patch.object(solver, "_find_speed_solution", return_value=speed_solution):
        result = solver.find_solution(
            pressure_constraint=FloatConstraint(value=500.0),
            inlet_stream=MagicMock(),
        )

    assert result.success is False
    assert result.failure is eos_failure
    anti_surge_strategy.apply.assert_not_called()
    pressure_control_strategy.apply.assert_not_called()
    runner.run.assert_not_called()
