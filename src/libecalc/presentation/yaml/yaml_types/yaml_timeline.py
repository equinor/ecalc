from typing import Annotated

from pydantic import ConfigDict, Field

from libecalc.ecalc_model.timeline_event import TimelineEventType
from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.yaml_default_datetime import YamlDefaultDatetime

type TimelineEventReference = str


class YamlTimelineEvent(YamlBase):
    title: Annotated[
        str | None,
        Field(
            title="TITLE",
            description="Human-friendly label for the event. Defaults to the event reference.",
        ),
    ] = None
    type: Annotated[
        TimelineEventType,
        Field(
            title="TYPE",
            description=f"Category of the event: {', '.join(TimelineEventType)}.",
        ),
    ]
    from_when: Annotated[
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
        dict[TimelineEventReference, YamlTimelineEvent],
        Field(
            title="EVENTS",
            description="Dated events that change the model permanently, e.g. a tie-in or a compressor rebundle. "
            "The key is the event reference, used by other parts of the model to refer to the event.",
        ),
    ] = {}
