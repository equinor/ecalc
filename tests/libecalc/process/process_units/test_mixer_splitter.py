import pytest

from ecalc_neqsim_wrapper.thermo import STANDARD_TEMPERATURE_KELVIN
from libecalc.process.process_units.mixer import Mixer
from libecalc.process.process_units.splitter import Splitter

# ── fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def inlet_stream(fluid_service, fluid_model_medium):
    return fluid_service.create_stream_from_standard_rate(
        fluid_model=fluid_model_medium,
        pressure_bara=50.0,
        temperature_kelvin=STANDARD_TEMPERATURE_KELVIN,
        standard_rate_m3_per_day=500_000,
    )


@pytest.fixture
def sidestream(fluid_service, fluid_model_medium):
    return fluid_service.create_stream_from_standard_rate(
        fluid_model=fluid_model_medium,
        pressure_bara=50.0,
        temperature_kelvin=STANDARD_TEMPERATURE_KELVIN,
        standard_rate_m3_per_day=100_000,
    )


# ── Mixer tests ───────────────────────────────────────────────────────────────


def test_mixer_adds_external_stream_rate(fluid_service, inlet_stream, sidestream):
    mixer = Mixer(fluid_service=fluid_service)
    mixer.set_stream(sidestream)

    outlet = mixer.propagate_stream(inlet_stream)

    assert outlet.standard_rate_sm3_per_day == pytest.approx(
        inlet_stream.standard_rate_sm3_per_day + sidestream.standard_rate_sm3_per_day, rel=1e-3
    )


def test_mixer_uses_lowest_pressure(fluid_service, fluid_model_medium):
    """Outlet pressure is the minimum of the two inlet pressures."""
    high_pressure_stream = fluid_service.create_stream_from_standard_rate(
        fluid_model=fluid_model_medium,
        pressure_bara=60.0,
        temperature_kelvin=STANDARD_TEMPERATURE_KELVIN,
        standard_rate_m3_per_day=500_000,
    )
    low_pressure_sidestream = fluid_service.create_stream_from_standard_rate(
        fluid_model=fluid_model_medium,
        pressure_bara=40.0,
        temperature_kelvin=STANDARD_TEMPERATURE_KELVIN,
        standard_rate_m3_per_day=100_000,
    )
    mixer = Mixer(fluid_service=fluid_service)
    mixer.set_stream(low_pressure_sidestream)

    outlet = mixer.propagate_stream(high_pressure_stream)

    assert outlet.pressure_bara == pytest.approx(40.0)


def test_mixer_raises_when_no_stream_set(fluid_service, inlet_stream):
    mixer = Mixer(fluid_service=fluid_service)

    with pytest.raises(ValueError, match="no external stream set"):
        mixer.propagate_stream(inlet_stream)


def test_mixer_stream_can_be_updated(fluid_service, inlet_stream, sidestream, fluid_model_medium):
    """set_stream replaces the previous external stream."""
    larger_sidestream = fluid_service.create_stream_from_standard_rate(
        fluid_model=fluid_model_medium,
        pressure_bara=50.0,
        temperature_kelvin=STANDARD_TEMPERATURE_KELVIN,
        standard_rate_m3_per_day=200_000,
    )
    mixer = Mixer(fluid_service=fluid_service)
    mixer.set_stream(sidestream)
    mixer.set_stream(larger_sidestream)

    outlet = mixer.propagate_stream(inlet_stream)

    assert outlet.standard_rate_sm3_per_day == pytest.approx(
        inlet_stream.standard_rate_sm3_per_day + larger_sidestream.standard_rate_sm3_per_day, rel=1e-3
    )


# ── Splitter tests ────────────────────────────────────────────────────────────


def test_splitter_removes_rate(fluid_service, inlet_stream):
    split_rate = 100_000.0
    splitter = Splitter(fluid_service=fluid_service, rate=split_rate)

    outlet = splitter.propagate_stream(inlet_stream)

    assert outlet.standard_rate_sm3_per_day == pytest.approx(
        inlet_stream.standard_rate_sm3_per_day - split_rate, rel=1e-3
    )


def test_splitter_preserves_pressure_and_temperature(fluid_service, inlet_stream):
    splitter = Splitter(fluid_service=fluid_service, rate=50_000.0)

    outlet = splitter.propagate_stream(inlet_stream)

    assert outlet.pressure_bara == pytest.approx(inlet_stream.pressure_bara)
    assert outlet.temperature_kelvin == pytest.approx(inlet_stream.temperature_kelvin)


def test_splitter_zero_rate_is_passthrough(fluid_service, inlet_stream):
    splitter = Splitter(fluid_service=fluid_service, rate=0.0)

    outlet = splitter.propagate_stream(inlet_stream)

    assert outlet.standard_rate_sm3_per_day == pytest.approx(inlet_stream.standard_rate_sm3_per_day, rel=1e-3)


def test_splitter_rate_can_be_updated(fluid_service, inlet_stream):
    splitter = Splitter(fluid_service=fluid_service, rate=50_000.0)
    splitter.set_rate(150_000.0)

    outlet = splitter.propagate_stream(inlet_stream)

    assert outlet.standard_rate_sm3_per_day == pytest.approx(
        inlet_stream.standard_rate_sm3_per_day - 150_000.0, rel=1e-3
    )


def test_splitter_get_split_stream_has_split_rate(fluid_service, inlet_stream):
    split_rate = 100_000.0
    splitter = Splitter(fluid_service=fluid_service, rate=split_rate)

    split_stream = splitter.get_split_stream(inlet_stream)

    assert split_stream.standard_rate_sm3_per_day == pytest.approx(split_rate, rel=1e-3)


def test_splitter_through_and_split_stream_sum_to_inlet(fluid_service, inlet_stream):
    split_rate = 100_000.0
    splitter = Splitter(fluid_service=fluid_service, rate=split_rate)

    through = splitter.propagate_stream(inlet_stream)
    split = splitter.get_split_stream(inlet_stream)

    assert through.standard_rate_sm3_per_day + split.standard_rate_sm3_per_day == pytest.approx(
        inlet_stream.standard_rate_sm3_per_day, rel=1e-3
    )
