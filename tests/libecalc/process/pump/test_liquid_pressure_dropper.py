from libecalc.common.units import UnitConstants
from libecalc.process.pump.liquid_stream import LiquidStream
from libecalc.process.pump.process_units.liquid_pressure_dropper import LiquidPressureDropper
from libecalc.testing.pump_test_data import DENSITY_KG_PER_M3


def _stream(rate_m3_per_hour: float) -> LiquidStream:
    return LiquidStream.from_volumetric_rate(
        volumetric_rate_m3_per_day=rate_m3_per_hour * UnitConstants.HOURS_PER_DAY,
        pressure_bara=10.0,
        density_kg_per_m3=DENSITY_KG_PER_M3,
    )


def test_stream_with_no_rate_passes_unchanged():
    """The pressure drop is above the pressure of the stream, as after a stopped pump."""
    pressure_dropper = LiquidPressureDropper(pressure_drop_bara=15.0)

    assert pressure_dropper.propagate_stream(_stream(0.0)) == _stream(0.0)
