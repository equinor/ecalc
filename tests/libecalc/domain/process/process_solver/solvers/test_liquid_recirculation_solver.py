import pytest

from libecalc.domain.process.entities.process_units.direct_mixer import DirectMixer
from libecalc.domain.process.entities.process_units.direct_splitter import DirectSplitter
from libecalc.domain.process.entities.process_units.pump import Pump
from libecalc.domain.process.process_pipeline.process_unit import create_process_unit_id
from libecalc.domain.process.process_solver.boundary import Boundary
from libecalc.domain.process.process_solver.configuration import RecirculationConfiguration
from libecalc.domain.process.process_solver.solvers.recirculation_solver import RecirculationSolver
from libecalc.domain.process.value_objects.chart import ChartCurve
from libecalc.domain.process.value_objects.liquid_stream import LiquidStream
from libecalc.presentation.yaml.mappers.charts.user_defined_chart_data import UserDefinedChartData

# Chart: single-speed at 3000 rpm, rates 10–100 m³/h, head 50_000–20_000 J/kg, η=0.7
_CHART = UserDefinedChartData(
    curves=[
        ChartCurve(
            speed_rpm=3000.0,
            rate_actual_m3_hour=[10.0, 50.0, 100.0],
            polytropic_head_joule_per_kg=[50_000.0, 40_000.0, 20_000.0],
            efficiency_fraction=[0.7, 0.7, 0.7],
        )
    ],
    control_margin=0.0,
)


def _make_pump() -> Pump:
    return Pump(process_unit_id=create_process_unit_id(), pump_chart=_CHART)


class _LiquidLoop:
    """Test helper: mixer → pump → splitter loop for liquid recirculation tests."""

    def __init__(self):
        self.mixer = DirectMixer(process_unit_id=create_process_unit_id(), mix_rate=0.0)
        self.pump = _make_pump()
        self.splitter = DirectSplitter(process_unit_id=create_process_unit_id(), split_rate=0.0)

    def set_recirculation_rate(self, rate: float):
        self.mixer.set_mix_rate(rate)
        self.splitter.set_split_rate(rate)

    def propagate_stream(self, inlet: LiquidStream) -> LiquidStream:
        mixed = self.mixer.propagate_stream(inlet)
        pumped = self.pump.propagate_stream(mixed)
        return self.splitter.propagate_stream(pumped)


def _stream(rate_m3h: float, pressure: float = 10.0, density: float = 800.0) -> LiquidStream:
    return LiquidStream(
        pressure_bara=pressure,
        density_kg_per_m3=density,
        mass_rate_kg_per_h=rate_m3h * density,
    )


def _make_solver(**kwargs) -> RecirculationSolver:
    return RecirculationSolver(
        search_strategy=kwargs.pop("search_strategy"),
        root_finding_strategy=kwargs.pop("root_finding_strategy"),
        recirculation_rate_boundary=kwargs.pop("recirculation_rate_boundary", Boundary(min=0.0, max=200.0 * 24)),
        **kwargs,
    )


class TestRecirculationSolverMinimumFlow:
    def test_no_recirc_needed_when_rate_above_minimum(self, search_strategy_factory, root_finding_strategy):
        """When inlet rate is already above minimum, solver returns zero recirculation."""
        loop = _LiquidLoop()
        inlet = _stream(rate_m3h=50.0)

        solver = _make_solver(
            search_strategy=search_strategy_factory(tolerance=1e-3),
            root_finding_strategy=root_finding_strategy,
        )

        def func(cfg: RecirculationConfiguration) -> LiquidStream:
            loop.set_recirculation_rate(cfg.recirculation_rate)
            return loop.propagate_stream(inlet)

        solution = solver.solve(func)

        assert solution.success
        assert solution.configuration.recirculation_rate == pytest.approx(0.0, abs=1e-3)

    def test_recirc_found_when_rate_below_minimum(self, search_strategy_factory, root_finding_strategy):
        """When inlet rate is below minimum, solver finds recirc that lifts pump to min flow."""
        loop = _LiquidLoop()
        inlet = _stream(rate_m3h=4.0)

        solver = _make_solver(
            search_strategy=search_strategy_factory(tolerance=1e-3),
            root_finding_strategy=root_finding_strategy,
        )

        def func(cfg: RecirculationConfiguration) -> LiquidStream:
            loop.set_recirculation_rate(cfg.recirculation_rate)
            return loop.propagate_stream(inlet)

        solution = solver.solve(func)

        assert solution.success
        assert solution.configuration.recirculation_rate >= 6.0 * 24 - 0.1

    def test_net_throughput_unchanged_after_solve(self, search_strategy_factory, root_finding_strategy):
        """After solving, net mass rate through the loop equals the original inlet rate."""
        loop = _LiquidLoop()
        inlet = _stream(rate_m3h=4.0, density=800.0)

        solver = _make_solver(
            search_strategy=search_strategy_factory(tolerance=1e-3),
            root_finding_strategy=root_finding_strategy,
        )

        def func(cfg: RecirculationConfiguration) -> LiquidStream:
            loop.set_recirculation_rate(cfg.recirculation_rate)
            return loop.propagate_stream(inlet)

        solution = solver.solve(func)
        outlet = loop.propagate_stream(inlet)

        assert solution.success
        assert outlet.mass_rate_kg_per_h == pytest.approx(inlet.mass_rate_kg_per_h, rel=1e-4)

    def test_stonewall_returns_failure(self, search_strategy_factory, root_finding_strategy):
        """When rate is above chart maximum, adding recirc cannot help — solver fails."""
        loop = _LiquidLoop()
        inlet = _stream(rate_m3h=200.0)

        solver = _make_solver(
            search_strategy=search_strategy_factory(tolerance=1e-3),
            root_finding_strategy=root_finding_strategy,
            recirculation_rate_boundary=Boundary(min=0.0, max=50.0),
        )

        def func(cfg: RecirculationConfiguration) -> LiquidStream:
            loop.set_recirculation_rate(cfg.recirculation_rate)
            return loop.propagate_stream(inlet)

        solution = solver.solve(func)

        assert not solution.success
