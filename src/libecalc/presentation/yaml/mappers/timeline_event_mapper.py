from libecalc.ecalc_model.timeline_event import TimelineEvent, TimelineEventType
from libecalc.presentation.yaml.yaml_types.yaml_timeline import TimelineEventReference, YamlTimelineEvent


class TimelineEventMapper:
    def map_events(self, yaml_timeline_events: dict[TimelineEventReference, YamlTimelineEvent]) -> list[TimelineEvent]:
        return [
            TimelineEvent(
                reference=reference,
                title=yaml_event.title or reference,
                type=TimelineEventType(yaml_event.type.value),
                from_date=yaml_event.from_date,
                description=yaml_event.description,
            )
            for reference, yaml_event in yaml_timeline_events.items()
        ]
