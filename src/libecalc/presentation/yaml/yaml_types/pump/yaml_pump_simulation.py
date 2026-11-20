import enum
from typing import Annotated, Literal

from pydantic import ConfigDict, Field

from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.components.yaml_expression_type import YamlExpressionType
from libecalc.presentation.yaml.yaml_types.process.yaml_process_references import InstanceReference
from libecalc.presentation.yaml.yaml_types.pump.yaml_liquid_stream import YamlLiquidInletStream
from libecalc.presentation.yaml.yaml_types.yaml_pump import PumpReference


class YamlPumpCommonStreamSetting(YamlBase):
    model_config = ConfigDict(title="PUMP_COMMON_STREAM_SETTING")

    rate_fractions: Annotated[
        list[YamlExpressionType],
        Field(
            title="RATE_FRACTIONS",
            description="Fraction of the inlet stream rate to each target, in the order of TARGETS.",
        ),
    ]


class YamlPumpCommonStreamDistribution(YamlBase):
    model_config = ConfigDict(title="PUMP_COMMON_STREAM_DISTRIBUTION")

    method: Literal["COMMON_STREAM"]
    inlet_stream: Annotated[
        YamlLiquidInletStream,
        Field(title="INLET_STREAM", description="The stream shared by the targets."),
    ]
    settings: Annotated[
        list[YamlPumpCommonStreamSetting],
        Field(
            title="SETTINGS",
            description="Ordered settings. The first setting where every pump is within its chart is used.",
        ),
    ]


class YamlPumpIndividualStreamDistribution(YamlBase):
    model_config = ConfigDict(title="PUMP_INDIVIDUAL_STREAM_DISTRIBUTION")

    method: Literal["INDIVIDUAL_STREAMS"]
    inlet_streams: Annotated[
        list[YamlLiquidInletStream],
        Field(title="INLET_STREAMS", description="One inlet stream per target, in the order of TARGETS."),
    ]


YamlPumpStreamDistribution = Annotated[
    YamlPumpCommonStreamDistribution | YamlPumpIndividualStreamDistribution,
    Field(discriminator="method"),
]


class YamlPumpPressureControl(enum.StrEnum):
    DOWNSTREAM_CHOKE = "DOWNSTREAM_CHOKE"
    NONE = "NONE"


class YamlPumpConstraint(YamlBase):
    model_config = ConfigDict(title="PUMP_CONSTRAINT")

    process_unit: Annotated[
        PumpReference | None,
        Field(
            title="PROCESS_UNIT",
            description="The PUMP of a pump process unit in this pipeline. If omitted, the constraint applies at the "
            "pipeline outlet, after the last pump.",
        ),
    ] = None
    outlet_pressure: Annotated[
        YamlExpressionType,
        Field(
            title="OUTLET_PRESSURE",
            description="Requested outlet pressure [bara].",
        ),
    ]
    pressure_control: Annotated[
        YamlPumpPressureControl,
        Field(
            title="PRESSURE_CONTROL",
            description="How to meet OUTLET_PRESSURE when the pump cannot run at a head low enough for it. "
            "DOWNSTREAM_CHOKE: a choke after the pump drops the excess discharge pressure. NONE: no choke, so the "
            "discharge pressure may be above OUTLET_PRESSURE. Defaults to NONE.",
        ),
    ] = YamlPumpPressureControl.NONE


class YamlPumpSimulation(YamlBase):
    model_config = ConfigDict(title="PUMP_SIMULATION")

    name: Annotated[str, Field(title="NAME", description="Name of the pump simulation.")]
    targets: Annotated[
        list[InstanceReference],
        Field(title="TARGETS", description="The pump pipelines in PUMP_PIPELINES to simulate together."),
    ]
    stream_distribution: Annotated[
        YamlPumpStreamDistribution,
        Field(title="STREAM_DISTRIBUTION", description="How the inlet rate is distributed over the targets."),
    ]
    constraints: Annotated[
        dict[InstanceReference, list[YamlPumpConstraint]],
        Field(title="CONSTRAINTS", description="Constraints per target. Key is the pump pipeline name."),
    ]
