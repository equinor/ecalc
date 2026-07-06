from libecalc.common.utils.ecalc_uuid import ecalc_id_generator
from libecalc.process.process_pipeline.process_unit import ProcessUnitId
from libecalc.process.pump.liquid_stream import SimplifiedLiquidStream
from libecalc.process.pump.pump import Pump

DENSITY = 1021.0


def _inlet(pressure_bara=10.0, rate_m3_per_day=15000.0, density=DENSITY):
    return SimplifiedLiquidStream.from_volumetric_rate(
        volumetric_rate_m3_per_day=rate_m3_per_day,
        pressure_bara=pressure_bara,
        density_kg_per_m3=density,
    )


def test_propagate_raises_inlet_to_discharge_pressure():
    inlet = _inlet(pressure_bara=10.0)
    pump = Pump()
    pump.set_discharge_pressure(90.0)

    outlet = pump.propagate_stream(inlet)

    assert outlet.pressure_bara == 90.0
    assert outlet.density_kg_per_m3 == inlet.density_kg_per_m3
    assert outlet.mass_rate_kg_per_h == inlet.mass_rate_kg_per_h


def test_pump_identity():
    provided_id = ProcessUnitId(ecalc_id_generator())
    assert Pump(process_unit_id=provided_id).get_id() == provided_id
    assert Pump().get_id() != Pump().get_id()
