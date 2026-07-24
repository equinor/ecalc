from datetime import datetime

import pytest

from libecalc.common.errors.ecalc_validation_error import EcalcValidationException
from libecalc.ecalc_model.ecalc_event import (
    EcalcEventType,
    ProcessEventType,
)
from libecalc.presentation.yaml.mappers.ecalc_event_mapper import EcalcEventMapper
from libecalc.presentation.yaml.yaml_types.process.yaml_process_simulation import (
    YamlEcalcEvent,
    YamlProcessEvent,
)


def _yaml_ecalc_event(
    name: str = "HIGH_RATE_EVENT",
    event_type: EcalcEventType = EcalcEventType.TIE_IN,
    start: datetime = datetime(2025, 1, 1),
    description: str | None = "Test event",
) -> YamlEcalcEvent:
    return YamlEcalcEvent(type=event_type, start=start, name=name, description=description)


def _yaml_process_event(
    name: str = "COMPRESSOR_REBUNDLE",
    event_type: ProcessEventType = ProcessEventType.INCREASED_GAS_RATE,
    ref: str = "HIGH_RATE_EVENT",
    description: str | None = "Increased gas rate event",
) -> YamlProcessEvent:
    return YamlProcessEvent(type=event_type, name=name, description=description, ref=ref)


class TestEcalcEventMapper:
    def test_maps_single_ecalc_event_without_process_events(self):
        mapper = EcalcEventMapper()
        ecalc_events = mapper.map_events(
            yaml_ecalc_events=[_yaml_ecalc_event()],
            yaml_process_events=[],
        )

        assert len(ecalc_events) == 1
        event = ecalc_events[0]
        assert event.name == "HIGH_RATE_EVENT"
        assert event.type == EcalcEventType.TIE_IN
        assert event.start == datetime(2025, 1, 1)
        assert event.description == "Test event"
        assert event.process_events == []

    def test_maps_ecalc_event_with_nested_process_events(self):
        mapper = EcalcEventMapper()
        ecalc_events = mapper.map_events(
            yaml_ecalc_events=[_yaml_ecalc_event()],
            yaml_process_events=[_yaml_process_event()],
        )

        assert len(ecalc_events) == 1
        event = ecalc_events[0]
        assert len(event.process_events) == 1

        pe = event.process_events[0]
        assert pe.name == "COMPRESSOR_REBUNDLE"
        assert pe.type == ProcessEventType.INCREASED_GAS_RATE
        assert pe.description == "Increased gas rate event"

    def test_maps_multiple_process_events_to_same_ecalc_event(self):
        mapper = EcalcEventMapper()
        ecalc_events = mapper.map_events(
            yaml_ecalc_events=[_yaml_ecalc_event(name="PHASE_2")],
            yaml_process_events=[
                _yaml_process_event(name="PE_A", ref="PHASE_2"),
                _yaml_process_event(name="PE_B", ref="PHASE_2", event_type=ProcessEventType.INCREASED_WATER_INJECTION),
            ],
        )

        assert len(ecalc_events) == 1
        assert len(ecalc_events[0].process_events) == 2
        assert ecalc_events[0].process_events[0].name == "PE_A"
        assert ecalc_events[0].process_events[1].name == "PE_B"
        assert ecalc_events[0].process_events[1].type == ProcessEventType.INCREASED_WATER_INJECTION

    def test_maps_multiple_ecalc_events_with_distributed_process_events(self):
        mapper = EcalcEventMapper()
        ecalc_events = mapper.map_events(
            yaml_ecalc_events=[
                _yaml_ecalc_event(name="EVENT_1", start=datetime(2025, 1, 1)),
                _yaml_ecalc_event(name="EVENT_2", start=datetime(2028, 6, 1)),
            ],
            yaml_process_events=[
                _yaml_process_event(name="PE_FOR_1", ref="EVENT_1"),
                _yaml_process_event(name="PE_FOR_2", ref="EVENT_2"),
            ],
        )

        assert len(ecalc_events) == 2
        assert ecalc_events[0].name == "EVENT_1"
        assert len(ecalc_events[0].process_events) == 1
        assert ecalc_events[0].process_events[0].name == "PE_FOR_1"

        assert ecalc_events[1].name == "EVENT_2"
        assert len(ecalc_events[1].process_events) == 1
        assert ecalc_events[1].process_events[0].name == "PE_FOR_2"

    def test_empty_events_returns_empty_list(self):
        mapper = EcalcEventMapper()
        ecalc_events = mapper.map_events(yaml_ecalc_events=[], yaml_process_events=[])
        assert ecalc_events == []

    def test_description_is_optional(self):
        mapper = EcalcEventMapper()
        events = mapper.map_events(
            yaml_ecalc_events=[_yaml_ecalc_event(description=None)],
            yaml_process_events=[_yaml_process_event(description=None)],
        )

        assert events[0].description is None
        assert events[0].process_events[0].description is None

    def test_duplicate_ecalc_event_name_raises(self):
        mapper = EcalcEventMapper()
        with pytest.raises(EcalcValidationException, match="Duplicate ECALC_EVENT name 'SAME_NAME'"):
            mapper.map_events(
                yaml_ecalc_events=[
                    _yaml_ecalc_event(name="SAME_NAME"),
                    _yaml_ecalc_event(name="SAME_NAME"),
                ],
                yaml_process_events=[],
            )

    def test_process_event_referencing_nonexistent_ecalc_event_raises(self):
        mapper = EcalcEventMapper()
        with pytest.raises(EcalcValidationException, match="does not exist"):
            mapper.map_events(
                yaml_ecalc_events=[_yaml_ecalc_event(name="EXISTING")],
                yaml_process_events=[_yaml_process_event(ref="NONEXISTENT")],
            )

    def test_process_event_error_message_lists_available_events(self):
        mapper = EcalcEventMapper()
        with pytest.raises(EcalcValidationException, match="Available: EVENT_A, EVENT_B"):
            mapper.map_events(
                yaml_ecalc_events=[
                    _yaml_ecalc_event(name="EVENT_A"),
                    _yaml_ecalc_event(name="EVENT_B"),
                ],
                yaml_process_events=[_yaml_process_event(ref="WRONG_REF")],
            )
