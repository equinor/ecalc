from typing import Annotated, Generic, Literal, Optional, TypeVar, Union

from pydantic import ConfigDict, Field

from libecalc.common.component_type import ComponentType
from libecalc.presentation.yaml.yaml_types.components.system.yaml_system_component_conditions import (
    YamlSystemComponentConditions,
)
from libecalc.presentation.yaml.yaml_types.components.train.yaml_train import YamlTrain
from libecalc.presentation.yaml.yaml_types.components.yaml_base import (
    YamlConsumerBase,
)
from libecalc.presentation.yaml.yaml_types.components.yaml_compressor import YamlCompressor
from libecalc.presentation.yaml.yaml_types.components.yaml_expression_type import (
    YamlExpressionType,
)
from libecalc.presentation.yaml.yaml_types.components.yaml_pump import YamlPump
from libecalc.presentation.yaml.yaml_types.yaml_stream_conditions import YamlStreamConditions

opt_expr_list = Optional[list[YamlExpressionType]]

PriorityID = str
StreamID = str
ConsumerID = str

YamlConsumerStreamConditions = dict[StreamID, YamlStreamConditions]
YamlConsumerStreamConditionsMap = dict[ConsumerID, YamlConsumerStreamConditions]
YamlPriorities = dict[PriorityID, YamlConsumerStreamConditionsMap]

TYamlConsumer = TypeVar(
    "TYamlConsumer", bound=Annotated[Union[YamlCompressor, YamlPump, YamlTrain], Field(discriminator="component_type")]
)


class YamlConsumerSystem(YamlConsumerBase, Generic[TYamlConsumer]):
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

    consumers: list[TYamlConsumer]
