from enum import StrEnum
from typing import Annotated, TypeVar

from pydantic import Field, model_validator

from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.process.yaml_process_references import (
    DefinitionReference,
    InstanceReference,
)
from libecalc.presentation.yaml.yaml_types.process.yaml_process_units import (
    YamlCompressorDefinition,
    YamlProcessUnitDefinition,
)
from libecalc.presentation.yaml.yaml_types.yaml_shaft import ShaftReference

TTarget = TypeVar("TTarget")


class YamlProcessUnitInstance[TTarget](YamlBase):
    target: TTarget | DefinitionReference
    name: str | None = None


class YamlShaftDrivenProcessUnitInstance(YamlProcessUnitInstance[YamlCompressorDefinition]):
    shaft: ShaftReference = Field(
        ...,
        title="SHAFT",
        description="Reference to a shaft defined in SHAFTS.",
    )


def describe_process_unit(process_unit: YamlProcessUnitInstance, position: int) -> str:
    if process_unit.name is not None:
        return f"'{process_unit.name}'"
    if isinstance(process_unit.target, str):
        return f"'{process_unit.target}'"
    return f"#{position} ({process_unit.target.type})"


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
        YamlCompressorDefinition | DefinitionReference,
        Field(
            title="CHANGE_FROM",
            description="Reference to the existing process unit template being replaced.",
        ),
    ]
    change_to: Annotated[
        YamlCompressorDefinition | DefinitionReference,
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
    name: str
    process_units: list[YamlShaftDrivenProcessUnitInstance | YamlProcessUnitInstance[YamlProcessUnitDefinition]]
    events: Annotated[
        list[YamlPipelineEvent],
        Field(
            title="EVENTS",
            description="Events that modify the pipeline over time, such as rebundling a compressor.",
        ),
    ] = []

    @model_validator(mode="after")
    def validate_single_shaft(self):
        shaft_names = {
            process_unit.shaft
            for process_unit in self.process_units
            if isinstance(process_unit, YamlShaftDrivenProcessUnitInstance)
        }
        if len(shaft_names) > 1:
            raise ValueError(
                f"Process pipeline '{self.name}' references multiple shafts: {', '.join(sorted(shaft_names))}. "
                f"Multiple shafts in one process pipeline are not supported yet."
            )
        return self
