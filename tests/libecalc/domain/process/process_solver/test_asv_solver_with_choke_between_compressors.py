"""Tests verifying ASVSolver correctly handles a Choke unit placed between compressor stages."""

import pytest
from inline_snapshot import snapshot

from libecalc.domain.process.entities.process_units.choke import Choke
from libecalc.domain.process.entities.shaft import VariableSpeedShaft
from libecalc.domain.process.process_solver.asv_solvers import ASVSolver
from libecalc.domain.process.process_solver.float_constraint import FloatConstraint
from libecalc.domain.process.process_system.process_unit import create_process_unit_id


@pytest.fixture
def shaft():
    return VariableSpeedShaft()


def _make_solver(
    shaft,
    stage1,
    stage2,
    fluid_service,
    individual_asv_control: bool,
    choke: Choke | None = None,
) -> ASVSolver:
    process_items = [stage1, choke, stage2] if choke is not None else [stage1, stage2]
    return ASVSolver(
        shaft=shaft,
        process_items=process_items,
        fluid_service=fluid_service,
        individual_asv_control=individual_asv_control,
    )


@pytest.mark.inlinesnapshot
@pytest.mark.snapshot
class TestCommonASVWithChokeBetweenCompressors:
    def test_without_choke_baseline(
        self,
        stream_factory,
        gas_compressor_factory,
        shaft,
        fluid_service,
        chart_data_factory,
    ):
        """Baseline: no manifold, establishes reference outlet pressure."""
        temperature = 300
        chart_1 = chart_data_factory.from_design_point(rate=1200, head=70000, efficiency=0.75)
        chart_2 = chart_data_factory.from_design_point(rate=900, head=50000, efficiency=0.72)

        solver = ASVSolver(
            shaft=shaft,
            process_items=[
                gas_compressor_factory(compressor_chart_data=chart_1, shaft=shaft),
                gas_compressor_factory(compressor_chart_data=chart_2, shaft=shaft),
            ],
            fluid_service=fluid_service,
            individual_asv_control=False,
        )
        inlet = stream_factory(standard_rate_m3_per_day=500_000.0, pressure_bara=30.0, temperature_kelvin=temperature)
        target = FloatConstraint(75.0)
        speed_sol, _ = solver.find_asv_solution(pressure_constraint=target, inlet_stream=inlet)

        assert speed_sol.success
        assert speed_sol.configuration.speed == snapshot(95.60149123260368)

    def test_with_choke_pressure_drop_requires_higher_speed(
        self,
        stream_factory,
        gas_compressor_factory,
        shaft,
        fluid_service,
        chart_data_factory,
    ):
        """A pressure-drop manifold between stages reduces interstage pressure, so the solver
        must run at a higher speed to still reach the same outlet target."""
        temperature = 300
        chart_1 = chart_data_factory.from_design_point(rate=1200, head=70000, efficiency=0.75)
        chart_2 = chart_data_factory.from_design_point(rate=900, head=50000, efficiency=0.72)

        manifold = Choke(
            process_unit_id=create_process_unit_id(),
            fluid_service=fluid_service,
            pressure_change=3.0,
        )

        solver_with = _make_solver(
            shaft=shaft,
            stage1=gas_compressor_factory(compressor_chart_data=chart_1, shaft=shaft),
            stage2=gas_compressor_factory(compressor_chart_data=chart_2, shaft=shaft),
            fluid_service=fluid_service,
            individual_asv_control=False,
            choke=manifold,
        )
        inlet = stream_factory(standard_rate_m3_per_day=500_000.0, pressure_bara=30.0, temperature_kelvin=temperature)
        target = FloatConstraint(75.0)
        speed_sol_with, _ = solver_with.find_asv_solution(pressure_constraint=target, inlet_stream=inlet)

        # Baseline speed (no choke) from test_without_choke_baseline
        baseline_speed = 95.60149123260368
        assert speed_sol_with.success
        assert speed_sol_with.configuration.speed > baseline_speed

    def test_zero_pressure_drop_choke_preserves_solve(
        self,
        stream_factory,
        gas_compressor_factory,
        shaft,
        fluid_service,
        chart_data_factory,
    ):
        """A manifold with zero pressure drop should give the same result as no manifold."""
        temperature = 300
        chart_1 = chart_data_factory.from_design_point(rate=1200, head=70000, efficiency=0.75)
        chart_2 = chart_data_factory.from_design_point(rate=900, head=50000, efficiency=0.72)

        manifold = Choke(
            process_unit_id=create_process_unit_id(),
            fluid_service=fluid_service,
            pressure_change=0.0,
        )

        solver = _make_solver(
            shaft=shaft,
            stage1=gas_compressor_factory(compressor_chart_data=chart_1, shaft=shaft),
            stage2=gas_compressor_factory(compressor_chart_data=chart_2, shaft=shaft),
            fluid_service=fluid_service,
            individual_asv_control=False,
            choke=manifold,
        )
        inlet = stream_factory(standard_rate_m3_per_day=500_000.0, pressure_bara=30.0, temperature_kelvin=temperature)
        speed_sol, _ = solver.find_asv_solution(pressure_constraint=FloatConstraint(75.0), inlet_stream=inlet)

        assert speed_sol.success
        assert speed_sol.configuration.speed == snapshot(95.60149123260368)


@pytest.mark.inlinesnapshot
@pytest.mark.snapshot
class TestIndividualASVWithChokeBetweenCompressors:
    def test_choke_pressure_drop_requires_higher_speed(
        self,
        stream_factory,
        gas_compressor_factory,
        fluid_service,
        chart_data_factory,
    ):
        """Individual ASV: a pressure-drop manifold between stages requires a higher speed."""
        temperature = 300
        chart_1 = chart_data_factory.from_design_point(rate=1200, head=70000, efficiency=0.75)
        chart_2 = chart_data_factory.from_design_point(rate=900, head=50000, efficiency=0.72)
        target = FloatConstraint(75.0)
        inlet = stream_factory(standard_rate_m3_per_day=500_000.0, pressure_bara=30.0, temperature_kelvin=temperature)

        shaft_a = VariableSpeedShaft()
        solver_without = _make_solver(
            shaft=shaft_a,
            stage1=gas_compressor_factory(compressor_chart_data=chart_1, shaft=shaft_a),
            stage2=gas_compressor_factory(compressor_chart_data=chart_2, shaft=shaft_a),
            fluid_service=fluid_service,
            individual_asv_control=True,
        )
        speed_without_choke, _ = solver_without.find_asv_solution(pressure_constraint=target, inlet_stream=inlet)

        shaft_b = VariableSpeedShaft()
        choke = Choke(
            process_unit_id=create_process_unit_id(),
            fluid_service=fluid_service,
            pressure_change=3.0,
        )
        solver_with = _make_solver(
            shaft=shaft_b,
            stage1=gas_compressor_factory(compressor_chart_data=chart_1, shaft=shaft_b),
            stage2=gas_compressor_factory(compressor_chart_data=chart_2, shaft=shaft_b),
            fluid_service=fluid_service,
            individual_asv_control=True,
            choke=choke,
        )
        speed_with_choke, _ = solver_with.find_asv_solution(pressure_constraint=target, inlet_stream=inlet)

        assert speed_with_choke.success
        assert speed_with_choke.configuration.speed > speed_without_choke.configuration.speed
