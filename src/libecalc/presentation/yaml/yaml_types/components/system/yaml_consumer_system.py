from typing import Annotated, Literal, Optional

from pydantic import ConfigDict, Field

from libecalc.common.component_type import ComponentType
from libecalc.presentation.yaml.yaml_types.components.system.priorities import YamlPriorities
from libecalc.presentation.yaml.yaml_types.components.system.type_aliases import TYamlConsumer
from libecalc.presentation.yaml.yaml_types.components.system.yaml_system_component_conditions import (
    YamlSystemComponentConditions,
)
from libecalc.presentation.yaml.yaml_types.components.yaml_base import (
    YamlConsumerBase,
)
from libecalc.presentation.yaml.yaml_types.components.yaml_expression_type import (
    YamlExpressionType,
)

opt_expr_list = Optional[list[YamlExpressionType]]


class YamlConsumerSystem(YamlConsumerBase):
    model_config = ConfigDict(title="ConsumerSystem")

    component_type: Literal[ComponentType.CONSUMER_SYSTEM_V2] = Field(
        ...,
        title="Type",
        description="The type of the component",
        alias="TYPE",
    )

    component_conditions: YamlSystemComponentConditions = Field(
        None,
        title="System component conditions",
        description="Contains conditions for the component, in this case the system.",
    )

    stream_conditions_priorities: YamlPriorities = Field(
        ...,
        title="Stream conditions priorities",
        description="A list of prioritised stream conditions per consumer.",
    )

    consumers: list[Annotated[TYamlConsumer, Field(discriminator="component_type")]]
