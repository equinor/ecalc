from datetime import datetime

from libecalc.ecalc_model.timeline_event import TimelineEvent, TimelineEventType
from libecalc.presentation.yaml.mappers.timeline_event_mapper import TimelineEventMapper
from libecalc.testing.process_builders import YamlTimelineEventBuilder


def test_maps_timeline_event():
    yaml_event = (
        YamlTimelineEventBuilder()
        .with_title("Rig on platform power")
        .with_type(TimelineEventType.FUEL_SWITCH)
        .with_from_when("2028-01-01")
        .validate()
    )

    assert TimelineEventMapper().map_events({"rig_on_platform_power": yaml_event}) == [
        TimelineEvent(
            reference="rig_on_platform_power",
            title="Rig on platform power",
            type=TimelineEventType.FUEL_SWITCH,
            from_when=datetime(2028, 1, 1),
            description=None,
        )
    ]


def test_title_defaults_to_reference():
    yaml_event = YamlTimelineEventBuilder().with_type(TimelineEventType.OTHER).with_from_when("2028-01-01").validate()

    [event] = TimelineEventMapper().map_events({"rig_on_platform_power": yaml_event})

    assert event.title == "rig_on_platform_power"
