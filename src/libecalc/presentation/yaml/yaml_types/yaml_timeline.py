from typing import Annotated

from pydantic import ConfigDict, Field

from libecalc.ecalc_model.timeline_event import TimelineEventType
from libecalc.ecalc_model.timeline_phase import TimelinePhaseType
from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.components.yaml_expression_type import YamlExpressionType
from libecalc.presentation.yaml.yaml_types.yaml_default_datetime import YamlDefaultDatetime

type TimelineEventReference = str
type TimelinePhaseReference = str


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


class YamlTimelinePhase(YamlBase):
    title: Annotated[
        str | None,
        Field(
            title="TITLE",
            description="Human-friendly label for the phase. Defaults to the phase reference.",
        ),
    ] = None
    type: Annotated[
        TimelinePhaseType,
        Field(
            title="TYPE",
            description=f"Category of the phase: {', '.join(TimelinePhaseType)}. Used as metadata only.",
        ),
    ]
    when: Annotated[
        YamlExpressionType,
        Field(
            title="WHEN",
            description="Expression telling when the phase is active, e.g. `SIM;DRILLING_FLAG` or `SIM;GAS_PROD > 0`. "
            "It must evaluate to 0 (inactive) or 1 (active) in every period.",
        ),
    ]
    description: Annotated[
        str | None,
        Field(
            title="DESCRIPTION",
            description="Human-readable description of the phase and its purpose.",
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
    phases: Annotated[
        dict[TimelinePhaseReference, YamlTimelinePhase],
        Field(
            title="PHASES",
            description="Named operating phases, e.g. drilling or production, that are active in some periods and "
            "inactive in others. The key is the phase reference, used by other parts of the model to refer to the "
            "phase.",
        ),
    ] = {}
