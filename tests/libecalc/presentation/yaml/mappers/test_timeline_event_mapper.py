from datetime import datetime

import pytest

from libecalc.common.errors.ecalc_validation_error import EcalcValidationException
from libecalc.ecalc_model.timeline_event import TimelineEvent, TimelineEventType
from libecalc.presentation.yaml.mappers.timeline_event_mapper import TimelineEventMapper
from libecalc.testing.process_builders import YamlTimelineEventBuilder


def test_maps_timeline_event():
    yaml_event = (
        YamlTimelineEventBuilder()
        .with_name("rig_on_platform_power")
        .with_type(TimelineEventType.FUEL_SWITCH)
        .with_from("2028-01-01")
        .validate()
    )

    assert TimelineEventMapper().map_events([yaml_event]) == [
        TimelineEvent(
            name="rig_on_platform_power",
            type=TimelineEventType.FUEL_SWITCH,
            from_=datetime(2028, 1, 1),
            description=None,
        )
    ]


def test_duplicate_event_names_raise():
    yaml_event = YamlTimelineEventBuilder().with_test_data().validate()

    with pytest.raises(EcalcValidationException, match="Duplicate TIMELINE event name"):
        TimelineEventMapper().map_events([yaml_event, yaml_event])
