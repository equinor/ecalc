from enum import StrEnum
from typing import Annotated, Any, Literal, Self, assert_never

from pydantic import ConfigDict, Field, model_validator

from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.process.yaml_process_references import (
    DefinitionReference,
    InstanceReference,
    validate_definition_reference_or_inline_model,
)
from libecalc.presentation.yaml.yaml_types.process.yaml_process_units import (
    YamlCompressorModelChart,
    YamlLiquidRemoverDefinition,
    YamlMixerDefinition,
    YamlPressureDropperDefinition,
    YamlSplitterDefinition,
    YamlTemperatureSetterDefinition,
)
from libecalc.presentation.yaml.yaml_types.yaml_compressor import CompressorReference
from libecalc.presentation.yaml.yaml_types.yaml_timeline import TimelineEventReference
from libecalc.presentation.yaml.yaml_types.yaml_version import V2, V3, V4, removed_field, yaml_element_lifecycle

CompressorModelOrReference = Annotated[
    DefinitionReference | YamlCompressorModelChart,
    validate_definition_reference_or_inline_model(YamlCompressorModelChart),
]


class YamlCompressorProcessUnitInstance(YamlBase):
    """A compressor from COMPRESSORS, run with a compressor model."""

    model_config = ConfigDict(
        title="COMPRESSOR_PROCESS_UNIT", json_schema_extra=yaml_element_lifecycle(available_since=V2)
    )
    type: Literal["COMPRESSOR"]

    model: CompressorModelOrReference = Field(
        ...,
        title="MODEL",
        description="The compressor model. Replaces TARGET. Other PROCESS_UNITs no longer supported. They must be defined inline without a reference.",
        json_schema_extra=yaml_element_lifecycle(available_since=V4),
    )
    compressor: CompressorReference = Field(
        ...,
        title="COMPRESSOR",
        description="Reference to a compressor defined in COMPRESSORS. CHANGE_TARGET and CONSTRAINTS.PROCESS_UNIT "
        "refer to this process unit by the compressor's name. The compressor's shaft is given in SHAFTS.",
        json_schema_extra=yaml_element_lifecycle(available_since=V3),
    )

    # REMOVED FIELDS
    target: Any = removed_field(
        title="TARGET",
        available_since=V2,
        removed_in=V4,
        message="Other PROCESS_UNITS can no longer be defined with TARGET.",
        replaced_by=("PROCESS_PIPELINES", "PROCESS_UNITS", "MODEL"),
    )
    shaft: Any = removed_field(title="SHAFT", available_since=V2, removed_in=V3, replaced_by=("SHAFTS", "COMPRESSORS"))
    # END REMOVED FIELDS

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
        TimelineEventReference,
        Field(
            title="REF",
            description="Reference to an event in TIMELINE.EVENTS. The change takes effect from the event date.",
        ),
    ]

    # REMOVED FIELDS
    change_from: Any = removed_field(
        title="CHANGE_FROM",
        available_since=V2,
        removed_in=V4,
        message="No longer in use. Remove. This is detected automatically.",
    )
    # END REMOVED FIELDS


# Every process unit is chosen by its TYPE, so an invalid unit reports the errors of its own type only.
YamlProcessUnit = Annotated[
    YamlCompressorProcessUnitInstance
    | YamlPressureDropperDefinition
    | YamlTemperatureSetterDefinition
    | YamlLiquidRemoverDefinition
    | YamlMixerDefinition
    | YamlSplitterDefinition,
    Field(discriminator="type"),
]


class YamlProcessPipeline(YamlBase):
    name: str
    process_units: Annotated[
        list[YamlProcessUnit],
        Field(
            title="PROCESS_UNITS",
            description="The process units in flow order, each given by its TYPE. Only a compressor process unit is "
            "referred to by name, its COMPRESSOR.",
        ),
    ]
    events: Annotated[
        list[YamlPipelineEvent],
        Field(
            title="EVENTS",
            description="Events that modify the pipeline over time, such as rebundling a compressor.",
        ),
    ] = []

    @property
    def compressors(self) -> list[CompressorReference]:
        """The compressors placed in this pipeline, in flow order."""
        return [unit.compressor for unit in self.process_units if isinstance(unit, YamlCompressorProcessUnitInstance)]

    @model_validator(mode="after")
    def validate_events(self) -> Self:
        """Rules for events that need only this pipeline. Each change type defines its own rule."""
        compressors = self.compressors
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
