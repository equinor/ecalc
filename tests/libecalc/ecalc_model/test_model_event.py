from datetime import datetime

from libecalc.ecalc_model.model_event import EnergyUnitEventChangeType, EnergyUnitModelEvent, active_model


def model_event(change_time: datetime, change_to: str) -> EnergyUnitModelEvent[str]:
    return EnergyUnitModelEvent(
        change_type=EnergyUnitEventChangeType.REBUNDLE,
        change_time=change_time,
        change_to=change_to,
    )


class TestActiveModel:
    def test_without_events_the_initial_model_is_active(self):
        assert active_model("initial", [], at=datetime(2030, 1, 1)) == "initial"

    def test_initial_model_is_active_before_the_first_event(self):
        events = [model_event(datetime(2025, 1, 1), "upgraded")]

        assert active_model("initial", events, at=datetime(2024, 12, 31)) == "initial"

    def test_event_is_active_from_its_change_time(self):
        events = [model_event(datetime(2025, 1, 1), "upgraded")]

        assert active_model("initial", events, at=datetime(2025, 1, 1)) == "upgraded"

    def test_latest_started_event_is_active_regardless_of_order(self):
        events = [
            model_event(datetime(2027, 1, 1), "second"),
            model_event(datetime(2025, 1, 1), "first"),
        ]

        assert active_model("initial", events, at=datetime(2026, 1, 1)) == "first"
        assert active_model("initial", events, at=datetime(2030, 1, 1)) == "second"
