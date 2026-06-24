from typing import Annotated

from pydantic import Field

from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.components.yaml_expression_type import YamlExpressionType
from libecalc.presentation.yaml.yaml_types.process.yaml_process_pipeline import (
    ProcessPipelineReference,
    YamlItem,
    YamlProcessPipeline,
)
from libecalc.presentation.yaml.yaml_types.process.yaml_process_references import ProcessUnitReference
from libecalc.presentation.yaml.yaml_types.process.yaml_stream_distribution import YamlStreamDistribution
from libecalc.process.process_solver.anti_surge.anti_surge_strategy import AntiSurgeType
from libecalc.process.process_solver.pressure_control.pressure_control_strategy import PressureControlType


class YamlProcessConstraint(YamlBase):
    process_unit: Annotated[
        ProcessUnitReference | None,
        Field(
            title="UNIT",
            description="Reference to a named unit within the pipeline. If omitted, the constraint applies to the pipeline outlet.",
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
        AntiSurgeType | None,
        Field(
            title="ANTI_SURGE",
            description="Anti-surge strategy to keep the compressor train within safe operating capacity.",
        ),
    ] = None


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
