from enum import StrEnum
from typing import Annotated

from pydantic import Field

from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.components.yaml_expression_type import YamlExpressionType
from libecalc.presentation.yaml.yaml_types.process.yaml_process_pipeline import (
    YamlItem,
    YamlProcessPipeline,
)
from libecalc.presentation.yaml.yaml_types.process.yaml_process_references import (
    EcalcEventReference,
    ProcessPipelineReference,
    ProcessUnitReference,
)
from libecalc.presentation.yaml.yaml_types.process.yaml_stream_distribution import YamlStreamDistribution
from libecalc.presentation.yaml.yaml_types.yaml_default_datetime import YamlDefaultDatetime
from libecalc.process.process_solver.anti_surge.anti_surge_strategy import AntiSurgeType
from libecalc.process.process_solver.pressure_control.pressure_control_strategy import PressureControlType


class EcalcEventType(StrEnum):
    PROCESS = "PROCESS"
    ENERGY = "ENERGY"
    ALL = "ALL"


class YamlEcalcEvent(YamlBase):
    type: Annotated[
        EcalcEventType,
        Field(
            title="TYPE",
            description="Domain affected by this event, e.g. PROCESS, ENERGY, or ALL.",
        ),
    ]
    start: Annotated[
        YamlDefaultDatetime,
        Field(
            title="START",
            description="Start date when this event takes effect.",
        ),
    ]
    # end: Annotated[  # Temp remove. Should be defined by next (for now)
    #    YamlDefaultDatetime,
    #    Field(
    #        title="END",
    #        description="End date when this event ceases to be in effect.",
    #    ),
    # ]
    name: Annotated[
        str,
        Field(
            title="NAME",
            description="Short identifier for the event.",
        ),
    ]
    description: Annotated[
        str | None,
        Field(
            title="DESCRIPTION",
            description="Human-readable description of the event and its purpose.",
        ),
    ] = None


class ProcessEventType(StrEnum):
    REBUNDLE = "REBUNDLE"
    REVAMP = "REVAMP"


class YamlProcessEvent(YamlBase):
    type: Annotated[
        ProcessEventType,
        Field(
            title="TYPE",
            description="Type of process event, e.g. REBUNDLE, REVAMP.",
        ),
    ]
    name: Annotated[
        str,
        Field(
            title="NAME",
            description="Short identifier for the process event.",
        ),
    ]
    description: Annotated[
        str | None,
        Field(
            title="DESCRIPTION",
            description="Human-readable description of the process event.",
        ),
    ] = None
    ref: Annotated[
        EcalcEventReference,
        Field(
            title="REF",
            description="Reference to a global ECALC_EVENT by name.",
        ),
    ]


class YamlProcessConstraint(YamlBase):
    process_unit: Annotated[
        ProcessUnitReference | None,
        Field(
            title="PROCESS_UNIT",
            description="Reference to a named unit within the pipeline. If omitted, the constraint applies to the last process unit in the pipeline section.",
        ),
    ] = None
    outlet_pressure: Annotated[
        YamlExpressionType,
        Field(
            title="OUTLET_PRESSURE",
            description="Target outlet pressure [bara].",
        ),
    ]
    pressure_control: Annotated[
        PressureControlType,
        Field(
            title="PRESSURE_CONTROL",
            description="How to meet the target pressure at this constraint point.",
        ),
    ]
    anti_surge: Annotated[
        AntiSurgeType,
        Field(
            title="ANTI_SURGE",
            description="Anti-surge strategy to keep the compressor train within safe operating capacity.",
        ),
    ]


class YamlProcessSimulation(YamlBase):
    name: str
    targets: Annotated[
        list[YamlItem[YamlProcessPipeline]],
        Field(title="TARGETS"),
    ]
    stream_distribution: YamlStreamDistribution
    constraints: Annotated[
        dict[ProcessPipelineReference, list[YamlProcessConstraint]],
        Field(
            title="CONSTRAINTS",
            description="Constraints per target. Key is pipeline name, value is list of constraints.",
        ),
    ]
