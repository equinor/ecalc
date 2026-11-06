from enum import StrEnum
from typing import Annotated, Self, assert_never

from pydantic import ConfigDict, Field, model_validator

from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.process.yaml_process_references import (
    DefinitionReference,
    InstanceReference,
    validate_definition_reference_or_inline_model,
)
from libecalc.presentation.yaml.yaml_types.process.yaml_process_units import (
    YamlCompressorModelChart,
    YamlProcessUnitDefinition,
)
from libecalc.presentation.yaml.yaml_types.yaml_compressor import CompressorReference
from libecalc.presentation.yaml.yaml_types.yaml_shaft import ShaftReference
from libecalc.presentation.yaml.yaml_types.yaml_version import V2, V3, V4, yaml_element_lifecycle

CompressorModelOrReference = Annotated[
    DefinitionReference | YamlCompressorModelChart,
    validate_definition_reference_or_inline_model(YamlCompressorModelChart),
]


class YamlProcessUnitInstance[TTarget](YamlBase):
    model_config = ConfigDict(title="PROCESS_UNIT")

    target: TTarget | DefinitionReference
    name: str | None = None

    def get_instance_reference(self) -> InstanceReference | None:
        """The name CHANGE_TARGET and CONSTRAINTS use to refer to this process unit, if any."""
        return self.name


class YamlCompressorProcessUnitInstance(YamlBase):
    model_config = ConfigDict(title="COMPRESSOR_PROCESS_UNIT")

    target: str | None = Field(
        None,
        title="TARGET",
        description="Reference to a compressor process unit defined in PROCESS_UNITS. From V4: Use MODEL instead.",
        json_schema_extra=yaml_element_lifecycle(
            available_since=V2, deprecated_since=V3, removed_since=V4, for_documentation_only=True
        ),
    )
    model: CompressorModelOrReference = Field(
        ...,
        title="MODEL",
        description="The compressor model. Replaces TARGET",
        json_schema_extra=yaml_element_lifecycle(available_since=V4),
    )
    compressor: CompressorReference = Field(
        ...,
        title="COMPRESSOR",
        description="Reference to a compressor defined in COMPRESSORS. CHANGE_TARGET and CONSTRAINTS.PROCESS_UNIT "
        "refer to this process unit by the compressor's name. The compressor's shaft is given in SHAFTS.",
    )

    # TODO: Available just to mark it as removed.
    shaft: ShaftReference | None = Field(
        None,
        title="SHAFT",
        description="Reference to a shaft defined in SHAFTS. "
        "This field is deprecated and has been removed in YAML_VERSION 3. Use the SHAFT > COMPRESSORS instead.",
        json_schema_extra=yaml_element_lifecycle(available_since=V2, removed_since=V3, for_documentation_only=True),
    )

    def get_instance_reference(self) -> InstanceReference:
        """The name CHANGE_TARGET and CONSTRAINTS use to refer to this process unit: the compressor's name."""
        return self.compressor


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
            description="Name of the process unit in the pipeline to change. For REBUNDLE, the COMPRESSOR of a "
            "compressor process unit in this pipeline.",
        ),
    ]
    change_from: Annotated[
        DefinitionReference | None,
        Field(
            None,
            title="CHANGE_FROM",
            description="Reference to the existing process unit template being replaced. V4: This is no longer needed. From is automatically deduced from target. Just remove.",
            json_schema_extra=yaml_element_lifecycle(available_since=V2, removed_since=V4, for_documentation_only=True),
        ),
    ]

    change_to: Annotated[
        CompressorModelOrReference,
        Field(
            title="CHANGE_TO",
            description="The compressor model to use from the event on.",
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
    process_units: list[YamlCompressorProcessUnitInstance | YamlProcessUnitInstance[YamlProcessUnitDefinition]]
    events: Annotated[
        list[YamlPipelineEvent],
        Field(
            title="EVENTS",
            description="Events that modify the pipeline over time, such as rebundling a compressor.",
        ),
    ] = []

    @model_validator(mode="after")
    def validate_events(self) -> Self:
        """Rules for events that need only this pipeline. Each change type defines its own rule."""
        compressors = [
            unit.compressor for unit in self.process_units if isinstance(unit, YamlCompressorProcessUnitInstance)
        ]
        for event in self.events:
            match event.change_type:
                case PipelineEventChangeType.REBUNDLE:
                    if event.change_target not in compressors:
                        raise ValueError(
                            f"REBUNDLE event targets '{event.change_target}', which is not a compressor in pipeline "
                            f"'{self.name}'. Compressors in this pipeline: {', '.join(compressors) or 'none'}."
                        )
                case _:
                    assert_never(event.change_type)
        return self
