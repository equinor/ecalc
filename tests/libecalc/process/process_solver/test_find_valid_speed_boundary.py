"""Tests that ShaftSpeedFinder handles EOS flash failures by narrowing the speed boundary.

Without the fix, CompressorThermodynamicCalculationError would escape uncaught.
"""

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from libecalc.domain.process.compressor.core.exceptions import CompressorThermodynamicCalculationError
from libecalc.domain.process.value_objects.chart import ChartCurve
from libecalc.process.fluid_stream.fluid_model import EoSModel, FluidComposition, FluidModel
from libecalc.process.process_pipeline.process_error import RateTooHighError
from libecalc.process.process_pipeline.process_unit import ProcessUnitId
from libecalc.process.process_solver.boundary import Boundary
from libecalc.process.process_solver.configuration import SpeedConfiguration
from libecalc.process.process_solver.finders.shaft_speed_finder import ShaftSpeedFinder
from libecalc.process.process_solver.solver import EosFailure
from libecalc.process.process_units.compressor import Compressor
from libecalc.process.shaft import VariableSpeedShaft
from libecalc.testing.chart_data_factory import ChartDataFactory


def _stream(pressure: float):
    return MagicMock(pressure_bara=pressure)


def _eos_error():
    raise CompressorThermodynamicCalculationError(operation="PH flash", reason="NeqSim failed", details={})


@pytest.fixture
def boundary():
    return Boundary(min=1000.0, max=5000.0)


def test_eos_failure_at_all_speeds_returns_thermodynamic_failure(
    boundary, search_strategy_factory, root_finding_strategy
):
    """If EOS fails at every speed, a EosFailure is returned rather than crashing."""

    def func(_config: SpeedConfiguration):
        _eos_error()

    finder = ShaftSpeedFinder(search_strategy_factory(), root_finding_strategy, boundary, target_pressure=80.0)

    finding = finder.find(func)

    assert not finding.success
    assert isinstance(finding.failure, EosFailure)


def test_eos_failure_at_max_narrows_boundary_and_finds_solution(
    boundary, search_strategy_factory, root_finding_strategy
):
    """EOS fails above a threshold; finder narrows and still locates the correct speed."""
    eos_threshold = 4000.0
    # pressure = speed / 50: at 1000 → 20 bar, at 4000 → 80 bar, target = 60 → speed = 3000
    target = 60.0

    def func(config: SpeedConfiguration):
        if config.speed > eos_threshold:
            _eos_error()
        return _stream(config.speed / 50)

    finder = ShaftSpeedFinder(search_strategy_factory(), root_finding_strategy, boundary, target_pressure=target)
    finding = finder.find(func)

    assert finding.failure is None
    assert finding.configuration.speed == pytest.approx(target * 50, rel=1e-3)


def test_eos_failure_at_min_narrows_boundary_and_finds_solution(
    boundary, search_strategy_factory, root_finding_strategy
):
    """EOS fails below a threshold; finder bisects up and still locates the correct speed."""
    eos_threshold = 2000.0
    # pressure = speed / 50: at 2000 → 40 bar, at 5000 → 100 bar, target = 80 → speed = 4000
    target = 80.0

    def func(config: SpeedConfiguration):
        if config.speed < eos_threshold:
            _eos_error()
        return _stream(config.speed / 50)

    finder = ShaftSpeedFinder(search_strategy_factory(), root_finding_strategy, boundary, target_pressure=target)
    finding = finder.find(func)

    assert finding.failure is None
    assert finding.configuration.speed == pytest.approx(target * 50, rel=1e-3)


def test_rate_too_high_at_max_still_returns_structured_failure(
    boundary, search_strategy_factory, root_finding_strategy
):
    """RateTooHighError at max speed still returns a structured Finding (unchanged behaviour)."""
    error = RateTooHighError(process_unit_id=ProcessUnitId(uuid4()))

    def func(config: SpeedConfiguration):
        if config.speed == boundary.max:
            raise error
        return _stream(config.speed / 50)

    finder = ShaftSpeedFinder(search_strategy_factory(), root_finding_strategy, boundary, target_pressure=60.0)
    finding = finder.find(func)

    assert finding.failure is not None


# ---------------------------------------------------------------------------
# Integration test — real NeqSim flash failure at max speed
# ---------------------------------------------------------------------------

# Heavy C3+ composition (MW ~22 kg/kmol).
# At 10 bara / 270 K, this chart's polytropic head at speeds above ~7 000 rpm
# pushes the Campbell outlet-pressure estimate well past 2 000 bara (the PH-flash
# pressure cap), causing NeqSim's PH flash to diverge with
# CompressorThermodynamicCalculationError.  Below ~7 000 rpm the flash converges.
_HEAVY_FLUID = FluidComposition(
    nitrogen=0.5,
    CO2=1.0,
    methane=45.0,
    ethane=15.0,
    propane=18.0,
    i_butane=5.0,
    n_butane=8.0,
    i_pentane=3.0,
    n_pentane=2.5,
    n_hexane=2.0,
)

# Chart spanning 1 000–15 000 rpm.  At max speed the compressor requires an
# outlet enthalpy that sends the PH flash into a non-convergent region.
_HEAVY_CHART = ChartDataFactory.from_curves(
    [
        ChartCurve(
            speed_rpm=1000,
            rate_actual_m3_hour=[100.0, 2000.0],
            polytropic_head_joule_per_kg=[20_000.0, 5_000.0],
            efficiency_fraction=[0.75, 0.75],
        ),
        ChartCurve(
            speed_rpm=15000,
            rate_actual_m3_hour=[100.0, 2000.0],
            polytropic_head_joule_per_kg=[4_000_000.0, 1_000_000.0],
            efficiency_fraction=[0.75, 0.75],
        ),
    ],
    control_margin=0.0,
)


def test_eos_failure_at_max_speed_with_real_fluid(fluid_service, search_strategy_factory, root_finding_strategy):
    """ShaftSpeedFinder narrows the speed boundary when EOS flash fails at max speed.

    Uses a heavy C3+ composition at cold / low-pressure inlet conditions where
    the PH flash diverges above ~10 500 rpm.  Without the fix, find() would
    propagate CompressorThermodynamicCalculationError; with it the finder bisects
    to the highest valid speed and locates the target pressure successfully.
    """
    fluid_model = FluidModel(composition=_HEAVY_FLUID, eos_model=EoSModel.SRK)

    shaft = VariableSpeedShaft()
    compressor = Compressor(compressor_chart=_HEAVY_CHART, fluid_service=fluid_service)
    shaft.connect(compressor)

    inlet = fluid_service.create_stream_from_standard_rate(
        fluid_model=fluid_model,
        pressure_bara=10.0,
        standard_rate_m3_per_day=500_000.0,
        temperature_kelvin=270.0,
    )

    def speed_func(config: SpeedConfiguration):
        shaft.set_speed(config.speed)
        return compressor.propagate_stream(inlet)

    # Target 300 bara is reachable near 2 600 rpm (well within the EOS-valid range).
    finder = ShaftSpeedFinder(
        search_strategy=search_strategy_factory(),
        root_finding_strategy=root_finding_strategy,
        boundary=Boundary(min=1000.0, max=15000.0),
        target_pressure=300.0,
    )
    finding = finder.find(speed_func)

    assert finding.failure is None
    shaft.set_speed(finding.configuration.speed)
    outlet = compressor.propagate_stream(inlet)
    assert outlet.pressure_bara == pytest.approx(300.0, rel=0.01)
