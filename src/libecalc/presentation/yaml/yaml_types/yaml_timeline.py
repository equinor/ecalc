from typing import Annotated

from pydantic import ConfigDict, Field, field_validator

from libecalc.common.string.string_utils import get_duplicates
from libecalc.ecalc_model.timeline_event import TimelineEventType
from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.yaml_default_datetime import YamlDefaultDatetime


class YamlTimelineEvent(YamlBase):
    name: Annotated[
        str,
        Field(
            title="NAME",
            description="Unique name of the event. Other parts of the model refer to the event by this name.",
        ),
    ]
    type: Annotated[
        TimelineEventType,
        Field(
            title="TYPE",
            description=f"Category of the event: {', '.join(TimelineEventType)}.",
        ),
    ]
    from_: Annotated[
        YamlDefaultDatetime,
        Field(
            alias="FROM",
            title="FROM",
            description="Date when the event takes effect. The change is permanent from this date.",
        ),
    ]
    description: Annotated[
        str | None,
        Field(
            title="DESCRIPTION",
            description="Human-readable description of the event and its purpose.",
        ),
    ] = None


class YamlTimeline(YamlBase):
    model_config = ConfigDict(title="Timeline")

    events: Annotated[
        list[YamlTimelineEvent],
        Field(
            title="EVENTS",
            description="Dated events that change the model permanently, e.g. a tie-in or a compressor rebundle.",
        ),
    ] = []

    @field_validator("events")
    @classmethod
    def validate_unique_event_names(cls, events: list[YamlTimelineEvent]) -> list[YamlTimelineEvent]:
        duplicates = get_duplicates([event.name for event in events])
        if duplicates:
            raise ValueError(f"Event names must be unique. Duplicated names: {', '.join(sorted(duplicates))}.")
        return events
