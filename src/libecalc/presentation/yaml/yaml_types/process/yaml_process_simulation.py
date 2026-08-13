from typing import Annotated, Literal

from pydantic import Field

from libecalc.ecalc_model.ecalc_event import EcalcEventType, ProcessEventType
from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.components.yaml_expression_type import YamlExpressionType
from libecalc.presentation.yaml.yaml_types.process.yaml_process_references import (
    DefinitionReference,
    InstanceReference,
)
from libecalc.presentation.yaml.yaml_types.process.yaml_stream_distribution import YamlStreamDistribution
from libecalc.presentation.yaml.yaml_types.yaml_default_datetime import YamlDefaultDatetime
from libecalc.process.process_solver.anti_surge.anti_surge_strategy import AntiSurgeType
from libecalc.process.process_solver.pressure_control.pressure_control_strategy import PressureControlType


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
    name: Annotated[
        InstanceReference,
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
        InstanceReference,
        Field(
            title="REF",
            description="Reference to a global ECALC_EVENT by name.",
        ),
    ]


class YamlProcessConstraint(YamlBase):
    process_unit: Annotated[
        InstanceReference | None,
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
        list[InstanceReference],
        Field(title="TARGETS"),
    ]
    stream_distribution: YamlStreamDistribution
    constraints: Annotated[
        dict[InstanceReference, list[YamlProcessConstraint]],
        Field(
            title="CONSTRAINTS",
            description="Constraints per target. Key is pipeline name, value is list of constraints.",
        ),
    ]


class YamlPumpProcessModel(YamlBase):
    chart: Annotated[
        DefinitionReference,
        Field(
            title="CHART",
            description="Reference to a pump chart defined in FACILITY_INPUTS.",
        ),
    ]
    minimum_flow_rate: Annotated[
        float | None,
        Field(
            title="MINIMUM_FLOW_RATE",
            description="Minimum pump flow in m3/h. Defaults to the chart minimum.",
        ),
    ] = None


class YamlPumpProcessInlet(YamlBase):
    rate: Annotated[
        YamlExpressionType,
        Field(title="RATE", description="Requested liquid rate in m3/day."),
    ]
    pressure: Annotated[
        YamlExpressionType,
        Field(title="PRESSURE", description="Pump suction pressure in bara."),
    ]
    density: Annotated[
        YamlExpressionType,
        Field(title="DENSITY", description="Liquid density in kg/m3."),
    ]


class YamlPumpProcessSimulation(YamlBase):
    type: Literal["PUMP"]
    name: str
    pump_model: Annotated[
        YamlPumpProcessModel,
        Field(title="PUMP_MODEL"),
    ]
    inlet: Annotated[
        YamlPumpProcessInlet,
        Field(title="INLET"),
    ]
    required_discharge_pressure: Annotated[
        YamlExpressionType,
        Field(
            title="REQUIRED_DISCHARGE_PRESSURE",
            description="Required pump discharge pressure in bara.",
        ),
    ]
