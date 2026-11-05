from libecalc.common.errors.ecalc_validation_error import EcalcValidationException
from libecalc.common.string.string_utils import get_duplicates
from libecalc.ecalc_model.timeline_event import TimelineEvent, TimelineEventType
from libecalc.presentation.yaml.yaml_types.yaml_timeline import YamlTimelineEvent


class TimelineEventMapper:
    def map_events(self, yaml_timeline_events: list[YamlTimelineEvent]) -> list[TimelineEvent]:
        duplicates = get_duplicates([yaml_event.name for yaml_event in yaml_timeline_events])
        if duplicates:
            raise EcalcValidationException(
                f"Duplicate TIMELINE event name(s): {', '.join(sorted(duplicates))}. Event names must be unique."
            )

        return [
            TimelineEvent(
                name=yaml_event.name,
                type=TimelineEventType(yaml_event.type.value),
                from_=yaml_event.from_,
                description=yaml_event.description,
            )
            for yaml_event in yaml_timeline_events
        ]
