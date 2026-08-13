from enum import StrEnum
from typing import Annotated, TypeVar

from pydantic import Field

from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.process.yaml_process_references import (
    DefinitionReference,
    InstanceReference,
)
from libecalc.presentation.yaml.yaml_types.process.yaml_process_units import (
    YamlProcessUnitDefinition,
)

TTarget = TypeVar("TTarget")


class YamlProcessUnitInstance[TTarget](YamlBase):
    target: TTarget | DefinitionReference
    name: InstanceReference | None = None


class PipelineEventAction(StrEnum):
    CHANGE = "CHANGE"
    ADD = "ADD"
    REMOVE = "REMOVE"


class PipelineEventChangeType(StrEnum):
    REBUNDLE = "REBUNDLE"


class YamlPipelineEvent(YamlBase):
    type: Annotated[
        PipelineEventAction,
        Field(
            title="TYPE",
            description="Action to perform: CHANGE, ADD, or REMOVE a process unit.",
        ),
    ]
    change_target: Annotated[
        InstanceReference,
        Field(
            title="CHANGE_TARGET",
            description="Name of the process unit in the pipeline to change.",
        ),
    ]
    change_from: Annotated[
        DefinitionReference,
        Field(
            title="CHANGE_FROM",
            description="Reference to the existing process unit template being replaced.",
        ),
    ]
    change_to: Annotated[
        DefinitionReference,
        Field(
            title="CHANGE_TO",
            description="Reference to the new process unit template to use.",
        ),
    ]
    change_type: Annotated[
        PipelineEventChangeType,
        Field(
            title="CHANGE_TYPE",
            description="Nature of the change, e.g. REBUNDLE (chart change, same physical compressor).",
        ),
    ]
    ref: Annotated[
        InstanceReference,
        Field(
            title="REF",
            description="Reference to a PROCESS_EVENT by name.",
        ),
    ]


class YamlProcessPipeline(YamlBase):
    name: InstanceReference
    process_units: list[YamlProcessUnitInstance[YamlProcessUnitDefinition]]
    events: Annotated[
        list[YamlPipelineEvent],
        Field(
            title="EVENTS",
            description="Events that modify the pipeline over time, such as rebundling a compressor.",
        ),
    ] = []
