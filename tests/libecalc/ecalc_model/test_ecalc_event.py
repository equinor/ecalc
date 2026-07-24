from datetime import datetime

from libecalc.ecalc_model.ecalc_event import (
    EcalcEvent,
    EcalcEventService,
    EcalcEventType,
    ProcessEvent,
    ProcessEventType,
)


class TestEcalcEventService:
    def _make_service(self) -> EcalcEventService:
        events = [
            EcalcEvent(
                name="EVENT_1",
                type=EcalcEventType.TIE_IN,
                start=datetime(2025, 1, 1),
                description=None,
                process_events=[
                    ProcessEvent(name="PE_A", type=ProcessEventType.INCREASED_GAS_RATE, description=None),
                    ProcessEvent(name="PE_B", type=ProcessEventType.OTHER, description=None),
                ],
            ),
            EcalcEvent(
                name="EVENT_2",
                type=EcalcEventType.OTHER,
                start=datetime(2028, 6, 1),
                description=None,
                process_events=[
                    ProcessEvent(name="PE_C", type=ProcessEventType.INCREASED_WATER_INJECTION, description=None),
                ],
            ),
        ]
        return EcalcEventService(ecalc_events=events)

    def test_get_event_by_name_found(self):
        service = self._make_service()
        event = service.get_event_by_name("EVENT_1")
        assert event is not None
        assert event.name == "EVENT_1"
        assert event.start == datetime(2025, 1, 1)

    def test_get_event_by_name_not_found(self):
        service = self._make_service()
        assert service.get_event_by_name("NONEXISTENT") is None

    def test_get_event_by_process_name_found(self):
        service = self._make_service()
        event = service.get_event_by_process_name("PE_A")
        assert event is not None
        assert event.name == "EVENT_1"

    def test_get_event_by_process_name_second_event(self):
        service = self._make_service()
        event = service.get_event_by_process_name("PE_C")
        assert event is not None
        assert event.name == "EVENT_2"
        assert event.start == datetime(2028, 6, 1)

    def test_get_event_by_process_name_not_found(self):
        service = self._make_service()
        assert service.get_event_by_process_name("NONEXISTENT") is None

    def test_empty_service(self):
        service = EcalcEventService(ecalc_events=[])
        assert service.get_event_by_name("ANY") is None
        assert service.get_event_by_process_name("ANY") is None
