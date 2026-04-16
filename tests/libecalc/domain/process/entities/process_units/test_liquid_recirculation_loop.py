import pytest

from libecalc.domain.process.entities.process_units.direct_mixer import DirectMixer
from libecalc.domain.process.entities.process_units.direct_splitter import DirectSplitter
from libecalc.domain.process.entities.process_units.pump import Pump
from libecalc.domain.process.process_pipeline.process_error import RateTooHighError, RateTooLowError
from libecalc.domain.process.process_pipeline.process_unit import create_process_unit_id
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


def _stream(rate_m3h: float, pressure: float = 10.0, density: float = 800.0) -> LiquidStream:
    return LiquidStream(
        pressure_bara=pressure,
        density_kg_per_m3=density,
        mass_rate_kg_per_h=rate_m3h * density,
    )


def _m3h_to_sm3_day(rate_m3h: float) -> float:
    return rate_m3h * 24.0


class _LiquidLoop:
    """Test helper: mixer → pump → splitter loop.

    On main, RecirculationLoop is a ConfigurationHandler that delegates
    set/get_recirculation_rate to mixer/splitter.  Stream propagation is
    done by ProcessPipelineRunner.  This helper wires the three units
    together for direct testing without the runner.
    """

    def __init__(self, recirculation_rate_sm3_day: float = 0.0):
        self.mixer = DirectMixer(process_unit_id=create_process_unit_id(), mix_rate=recirculation_rate_sm3_day)
        self.pump = _make_pump()
        self.splitter = DirectSplitter(process_unit_id=create_process_unit_id(), split_rate=recirculation_rate_sm3_day)

    def set_recirculation_rate(self, rate: float):
        self.mixer.set_mix_rate(rate)
        self.splitter.set_split_rate(rate)

    def get_recirculation_rate(self) -> float:
        return self.mixer.get_mix_rate()

    def propagate_stream(self, inlet: LiquidStream) -> LiquidStream:
        mixed = self.mixer.propagate_stream(inlet)
        pumped = self.pump.propagate_stream(mixed)
        return self.splitter.propagate_stream(pumped)


def _make_loop(recirculation_rate_m3_per_h: float = 0.0) -> _LiquidLoop:
    return _LiquidLoop(recirculation_rate_sm3_day=_m3h_to_sm3_day(recirculation_rate_m3_per_h))


class TestDirectMixerWithLiquidStream:
    def test_adds_flow_to_mass_rate(self):
        mixer = DirectMixer(process_unit_id=create_process_unit_id(), mix_rate=_m3h_to_sm3_day(20.0))
        inlet = _stream(rate_m3h=30.0, density=800.0)
        outlet = mixer.propagate_stream(inlet)
        assert outlet.volumetric_rate_m3_per_hour == pytest.approx(50.0)
        assert outlet.density_kg_per_m3 == inlet.density_kg_per_m3
        assert outlet.pressure_bara == inlet.pressure_bara

    def test_zero_recirc_is_passthrough(self):
        mixer = DirectMixer(process_unit_id=create_process_unit_id(), mix_rate=0.0)
        inlet = _stream(rate_m3h=30.0)
        outlet = mixer.propagate_stream(inlet)
        assert outlet.mass_rate_kg_per_h == inlet.mass_rate_kg_per_h


class TestDirectSplitterWithLiquidStream:
    def test_removes_flow_from_mass_rate(self):
        splitter = DirectSplitter(process_unit_id=create_process_unit_id(), split_rate=_m3h_to_sm3_day(20.0))
        inlet = _stream(rate_m3h=50.0, density=800.0)
        outlet = splitter.propagate_stream(inlet)
        assert outlet.volumetric_rate_m3_per_hour == pytest.approx(30.0)
        assert outlet.density_kg_per_m3 == inlet.density_kg_per_m3
        assert outlet.pressure_bara == inlet.pressure_bara

    def test_mixer_splitter_are_inverse(self):
        rate = _m3h_to_sm3_day(20.0)
        mixer = DirectMixer(process_unit_id=create_process_unit_id(), mix_rate=rate)
        splitter = DirectSplitter(process_unit_id=create_process_unit_id(), split_rate=rate)
        inlet = _stream(rate_m3h=40.0)
        mixed = mixer.propagate_stream(inlet)
        split = splitter.propagate_stream(mixed)
        assert split.mass_rate_kg_per_h == pytest.approx(inlet.mass_rate_kg_per_h)


class TestRecirculationLoopPumpBehaviour:
    def test_zero_recirc_is_passthrough(self):
        """At zero recirculation, loop behaves identically to bare Pump."""
        loop = _make_loop(recirculation_rate_m3_per_h=0.0)
        inlet = _stream(rate_m3h=50.0)
        outlet = loop.propagate_stream(inlet)
        assert outlet.mass_rate_kg_per_h == pytest.approx(inlet.mass_rate_kg_per_h)
        assert outlet.pressure_bara > inlet.pressure_bara

    def test_recirc_raises_effective_pump_flow_above_minimum(self):
        """Recirculation flow lifts the pump's effective rate above the chart minimum."""
        loop = _make_loop(recirculation_rate_m3_per_h=8.0)
        inlet = _stream(rate_m3h=4.0)
        outlet = loop.propagate_stream(inlet)
        assert outlet.pressure_bara > inlet.pressure_bara

    def test_insufficient_recirc_still_raises(self):
        """When recirculation is not enough to reach minimum flow, RateTooLowError propagates."""
        loop = _make_loop(recirculation_rate_m3_per_h=0.0)
        inlet = _stream(rate_m3h=1.0)
        with pytest.raises(RateTooLowError):
            loop.propagate_stream(inlet)

    def test_stonewall_still_raises(self):
        """Even with recirc, stonewall (rate > max) raises RateTooHighError."""
        loop = _make_loop(recirculation_rate_m3_per_h=200.0)
        inlet = _stream(rate_m3h=200.0)
        with pytest.raises(RateTooHighError):
            loop.propagate_stream(inlet)

    def test_set_get_recirculation_rate(self):
        loop = _make_loop(recirculation_rate_m3_per_h=0.0)
        loop.set_recirculation_rate(_m3h_to_sm3_day(15.0))
        assert loop.get_recirculation_rate() == pytest.approx(_m3h_to_sm3_day(15.0))

    def test_net_throughput_unchanged(self):
        """Outlet mass rate equals inlet mass rate regardless of recirculation."""
        loop = _make_loop(recirculation_rate_m3_per_h=30.0)
        inlet = _stream(rate_m3h=50.0)
        outlet = loop.propagate_stream(inlet)
        assert outlet.mass_rate_kg_per_h == pytest.approx(inlet.mass_rate_kg_per_h)
