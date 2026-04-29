"""Integration test: ProcessPipelineRunner end-to-end with pump.

Tests that the entire solver stack (OutletPressureSolver → SpeedSolver →
RecirculationSolver) works with a variable-speed pump pipeline using LiquidStream.
This verifies Decision 8: the unified ProcessPipelineRunner accepts both gas
compressor and liquid pump pipelines via the ProcessUnit protocol.
"""

import pytest

from libecalc.domain.process.entities.process_units.pump import Pump
from libecalc.domain.process.entities.shaft import VariableSpeedShaft
from libecalc.domain.process.process_pipeline.process_unit import create_process_unit_id
from libecalc.domain.process.process_solver.float_constraint import FloatConstraint
from libecalc.domain.process.process_solver.solvers.recirculation_solver import RecirculationConfiguration
from libecalc.domain.process.value_objects.chart import ChartCurve
from libecalc.domain.process.value_objects.liquid_stream import LiquidStream
from libecalc.testing.chart_data_factory import ChartDataFactory

# Variable-speed pump chart: 2 speeds (3000, 4200 rpm)
# Rate range: 20–120 m³/h
# Head range: ~5000–2000 J/kg → ~50–20 bar rise for water at 1030 kg/m³
# Efficiency: 0.72
_PUMP_CHART = ChartDataFactory.from_curves(
    curves=[
        ChartCurve(
            speed_rpm=3000.0,
            rate_actual_m3_hour=[20.0, 60.0, 120.0],
            polytropic_head_joule_per_kg=[5000.0, 4000.0, 2000.0],
            efficiency_fraction=[0.72, 0.72, 0.72],
        ),
        ChartCurve(
            speed_rpm=4200.0,
            rate_actual_m3_hour=[20.0, 60.0, 120.0],
            polytropic_head_joule_per_kg=[5250.0, 4200.0, 2100.0],
            efficiency_fraction=[0.72, 0.72, 0.72],
        ),
    ],
    control_margin=0.0,
)


def _make_inlet(rate_m3h: float = 50.0, pressure: float = 10.0, density: float = 1030.0) -> LiquidStream:
    """Water injection stream at typical conditions."""
    return LiquidStream(
        pressure_bara=pressure,
        density_kg_per_m3=density,
        mass_rate_kg_per_h=rate_m3h * density,
    )


@pytest.fixture
def pump():
    return Pump(process_unit_id=create_process_unit_id(), pump_chart=_PUMP_CHART)


@pytest.fixture
def shaft():
    return VariableSpeedShaft()


class TestPumpPipelineIntegration:
    """End-to-end tests: ProcessPipelineRunner with pump, shaft, recirculation."""

    def test_pump_pipeline_finds_speed_for_target_pressure(
        self,
        pump,
        shaft,
        with_common_asv,
        process_pipeline_factory,
        process_runner_factory,
        common_asv_anti_surge_strategy_factory,
        common_asv_pressure_control_strategy_factory,
        outlet_pressure_solver_factory,
    ):
        """SpeedSolver finds the RPM needed to reach target outlet pressure."""
        shaft.connect(pump)
        common_asv, pipeline_units = with_common_asv([pump])

        runner = process_runner_factory(units=pipeline_units, configuration_handlers=[shaft, common_asv])
        process_pipeline = process_pipeline_factory(units=pipeline_units)

        anti_surge = common_asv_anti_surge_strategy_factory(
            runner=runner, recirculation_loop_id=common_asv.get_id(), first_unit=pump
        )
        pressure_control = common_asv_pressure_control_strategy_factory(
            runner=runner, recirculation_loop_id=common_asv.get_id(), first_unit=pump
        )
        solver = outlet_pressure_solver_factory(
            shaft=shaft,
            runner=runner,
            anti_surge_strategy=anti_surge,
            pressure_control_strategy=pressure_control,
            process_pipeline_id=process_pipeline.get_id(),
        )

        inlet = _make_inlet(rate_m3h=50.0, pressure=10.0)

        # Target: 40 bara outlet from 10 bara inlet (30 bar rise)
        # Head needed: 30e5 / 1030 ≈ 2913 J/kg — within chart range
        target = FloatConstraint(40.0)
        solution = solver.find_solution(pressure_constraint=target, inlet_stream=inlet)

        assert solution.success

        # Verify speed was found
        config_dict = {c.configuration_handler_id: c.value for c in solution.configuration}
        speed = config_dict[shaft.get_id()].speed
        assert 3000.0 <= speed <= 4200.0

        # Verify outlet pressure matches target
        runner.apply_configurations(solution.configuration)
        outlet = runner.run(inlet_stream=inlet)
        assert outlet.pressure_bara == pytest.approx(target.value, rel=1e-3)

    def test_pump_exposes_shaft_power_after_solve(
        self,
        pump,
        shaft,
        with_common_asv,
        process_pipeline_factory,
        process_runner_factory,
        common_asv_anti_surge_strategy_factory,
        common_asv_pressure_control_strategy_factory,
        outlet_pressure_solver_factory,
    ):
        """After solving, pump exposes shaft power, head, and efficiency."""
        shaft.connect(pump)
        common_asv, pipeline_units = with_common_asv([pump])

        runner = process_runner_factory(units=pipeline_units, configuration_handlers=[shaft, common_asv])
        process_pipeline = process_pipeline_factory(units=pipeline_units)

        anti_surge = common_asv_anti_surge_strategy_factory(
            runner=runner, recirculation_loop_id=common_asv.get_id(), first_unit=pump
        )
        pressure_control = common_asv_pressure_control_strategy_factory(
            runner=runner, recirculation_loop_id=common_asv.get_id(), first_unit=pump
        )
        solver = outlet_pressure_solver_factory(
            shaft=shaft,
            runner=runner,
            anti_surge_strategy=anti_surge,
            pressure_control_strategy=pressure_control,
            process_pipeline_id=process_pipeline.get_id(),
        )

        inlet = _make_inlet(rate_m3h=50.0, pressure=10.0)
        target = FloatConstraint(40.0)
        solution = solver.find_solution(pressure_constraint=target, inlet_stream=inlet)

        assert solution.success

        # Apply solution and run to populate pump state
        runner.apply_configurations(solution.configuration)
        runner.run(inlet_stream=inlet)

        # Pump should now expose valid results
        assert pump.last_shaft_power_mw > 0
        assert pump.last_head_joule_per_kg > 0
        assert 0 < pump.last_efficiency <= 1.0

        # Verify physics: P = ṁ × head / η / 1e6
        # Use pump's actual mass rate (may include recirculation)
        mass_rate_kg_s = pump._last_mass_rate_kg_per_s
        expected_power = mass_rate_kg_s * pump.last_head_joule_per_kg / pump.last_efficiency / 1e6
        assert pump.last_shaft_power_mw == pytest.approx(expected_power, rel=1e-6)

    def test_pump_pipeline_with_recirculation(
        self,
        shaft,
        with_common_asv,
        process_pipeline_factory,
        process_runner_factory,
        common_asv_anti_surge_strategy_factory,
        common_asv_pressure_control_strategy_factory,
        outlet_pressure_solver_factory,
    ):
        """When rate is below minimum, anti-surge recirculation kicks in."""
        # Use a chart with higher minimum rate to force recirculation
        chart = ChartDataFactory.from_curves(
            curves=[
                ChartCurve(
                    speed_rpm=3000.0,
                    rate_actual_m3_hour=[40.0, 80.0, 120.0],
                    polytropic_head_joule_per_kg=[5000.0, 4000.0, 2000.0],
                    efficiency_fraction=[0.72, 0.72, 0.72],
                ),
                ChartCurve(
                    speed_rpm=4200.0,
                    rate_actual_m3_hour=[40.0, 80.0, 120.0],
                    polytropic_head_joule_per_kg=[5250.0, 4200.0, 2100.0],
                    efficiency_fraction=[0.72, 0.72, 0.72],
                ),
            ],
            control_margin=0.0,
        )
        pump = Pump(process_unit_id=create_process_unit_id(), pump_chart=chart)
        shaft.connect(pump)

        common_asv, pipeline_units = with_common_asv([pump])
        runner = process_runner_factory(units=pipeline_units, configuration_handlers=[shaft, common_asv])
        process_pipeline = process_pipeline_factory(units=pipeline_units)

        anti_surge = common_asv_anti_surge_strategy_factory(
            runner=runner, recirculation_loop_id=common_asv.get_id(), first_unit=pump
        )
        pressure_control = common_asv_pressure_control_strategy_factory(
            runner=runner, recirculation_loop_id=common_asv.get_id(), first_unit=pump
        )
        solver = outlet_pressure_solver_factory(
            shaft=shaft,
            runner=runner,
            anti_surge_strategy=anti_surge,
            pressure_control_strategy=pressure_control,
            process_pipeline_id=process_pipeline.get_id(),
        )

        # Inlet rate of 20 m³/h is below chart minimum of 40 m³/h → needs recirculation
        inlet = _make_inlet(rate_m3h=20.0, pressure=10.0)
        target = FloatConstraint(40.0)

        solution = solver.find_solution(pressure_constraint=target, inlet_stream=inlet)

        assert solution.success

        # Verify recirculation was applied
        recirc_configs = [c for c in solution.configuration if isinstance(c.value, RecirculationConfiguration)]
        assert len(recirc_configs) > 0
        assert recirc_configs[0].value.recirculation_rate > 0

        # Verify outlet pressure matches target
        runner.apply_configurations(solution.configuration)
        outlet = runner.run(inlet_stream=inlet)
        assert outlet.pressure_bara == pytest.approx(target.value, rel=1e-3)

        # Net throughput should equal inlet rate (recirculation is internal)
        assert outlet.mass_rate_kg_per_h == pytest.approx(inlet.mass_rate_kg_per_h, rel=1e-3)
