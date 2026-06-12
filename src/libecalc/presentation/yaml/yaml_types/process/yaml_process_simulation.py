from typing import Annotated, Literal

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


class YamlProcessConstraint(YamlBase):
    target: Annotated[
        ProcessPipelineReference,
        Field(
            title="TARGET",
            description="Reference to the process pipeline this constraint applies to.",
        ),
    ]
    unit: Annotated[
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


class YamlProcessSimulation(YamlBase):
    name: str
    targets: Annotated[
        list[YamlItem[YamlProcessPipeline]],
        Field(title="TARGETS"),
    ]
    stream_distribution: YamlStreamDistribution
    pressure_control: Annotated[
        dict[
            ProcessPipelineReference,
            Literal[
                "COMMON_ASV", "INDIVIDUAL_ASV_RATE", "INDIVIDUAL_ASV_PRESSURE", "DOWNSTREAM_CHOKE", "UPSTREAM_CHOKE"
            ],
        ],
        Field(
            title="PRESSURE_CONTROLS",
            description="Pressure control strategy per target",
        ),
    ]
    constraints: Annotated[
        list[YamlProcessConstraint],
        Field(
            title="CONSTRAINTS",
            description="Constraints per target.",
        ),
    ]
