import uuid

from libecalc.common.fixed_speed_pressure_control import FixedSpeedPressureControl
from libecalc.domain.process.process_system.pressure_target import PressureTarget
from libecalc.domain.process.process_system.process_unit import ProcessUnitId


def _make_id() -> ProcessUnitId:
    return ProcessUnitId(uuid.uuid4())


class TestPressureTarget:
    def test_propagate_stream_is_noop(self, stream_factory):
        """propagate_stream must return the inlet stream unchanged."""
        target = PressureTarget(process_unit_id=_make_id(), target_pressure_bara=50.0)
        inlet = stream_factory(standard_rate_m3_per_day=500_000.0, pressure_bara=30.0, temperature_kelvin=300.0)
        outlet = target.propagate_stream(inlet_stream=inlet)
        assert outlet is inlet

    def test_target_pressure_stored(self):
        target = PressureTarget(process_unit_id=_make_id(), target_pressure_bara=75.0)
        assert target.target_pressure_bara == 75.0

    def test_has_target_pressure(self):
        target = PressureTarget(process_unit_id=_make_id(), target_pressure_bara=50.0)
        assert target.has_target_pressure is True

    def test_downstream_pressure_control_default_is_none(self):
        target = PressureTarget(process_unit_id=_make_id(), target_pressure_bara=50.0)
        assert target.downstream_pressure_control is None

    def test_downstream_pressure_control_stored(self):
        target = PressureTarget(
            process_unit_id=_make_id(),
            target_pressure_bara=50.0,
            downstream_pressure_control=FixedSpeedPressureControl.DOWNSTREAM_CHOKE,
        )
        assert target.downstream_pressure_control == FixedSpeedPressureControl.DOWNSTREAM_CHOKE

    def test_get_id_returns_id(self):
        uid = _make_id()
        target = PressureTarget(process_unit_id=uid, target_pressure_bara=50.0)
        assert target.get_id() == uid
