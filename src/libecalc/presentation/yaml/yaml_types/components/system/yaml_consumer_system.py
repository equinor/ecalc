from datetime import datetime
from typing import Dict, Generic, List, Literal, Optional, TypeVar, Union

try:
    from pydantic.v1 import Field
    from pydantic.v1.generics import GenericModel
except ImportError:
    from pydantic import Field
    from pydantic.generics import GenericModel

from libecalc import dto
from libecalc.common.time_utils import Period, define_time_model_for_period
from libecalc.dto.base import ComponentType
from libecalc.dto.components import Crossover, SystemComponentConditions
from libecalc.dto.types import ConsumptionType
from libecalc.expression import Expression
from libecalc.expression.expression import ExpressionType
from libecalc.presentation.yaml.yaml_entities import References
from libecalc.presentation.yaml.yaml_types.components.system.yaml_system_component_conditions import (
    YamlSystemComponentConditions,
)
from libecalc.presentation.yaml.yaml_types.components.train.yaml_train import YamlTrain
from libecalc.presentation.yaml.yaml_types.components.yaml_base import (
    YamlConsumerBase,
)
from libecalc.presentation.yaml.yaml_types.components.yaml_compressor import (
    YamlCompressor,
)
from libecalc.presentation.yaml.yaml_types.components.yaml_pump import YamlPump
from libecalc.presentation.yaml.yaml_types.yaml_stream_conditions import (
    YamlStreamConditions,
)

opt_expr_list = Optional[List[ExpressionType]]

PriorityID = str
StreamID = str
ConsumerID = str

YamlConsumerStreamConditions = Dict[StreamID, YamlStreamConditions]
YamlConsumerStreamConditionsMap = Dict[ConsumerID, YamlConsumerStreamConditions]
YamlPriorities = Dict[PriorityID, YamlConsumerStreamConditionsMap]

TYamlConsumer = TypeVar("TYamlConsumer", bound=Union[YamlCompressor, YamlPump, YamlTrain[YamlCompressor]])


class YamlConsumerSystem(YamlConsumerBase, GenericModel, Generic[TYamlConsumer]):
    class Config:
        title = "ConsumerSystem"

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

    consumers: List[TYamlConsumer]

    def to_dto(
        self,
        regularity: Dict[datetime, Expression],
        consumes: ConsumptionType,
        references: References,
        target_period: Period,
        fuel: Optional[Dict[datetime, dto.types.FuelType]] = None,
    ) -> dto.components.ConsumerSystem:
        consumers = [
            consumer.to_dto(
                references=references,
                consumes=consumes,
                regularity=regularity,
                target_period=target_period,
                fuel=fuel,
                category=self.category,
            )
            for consumer in self.consumers
        ]
        consumer_name_to_id_map = {consumer.name: consumer.id for consumer in consumers}

        if self.component_conditions is not None:
            component_conditions = SystemComponentConditions(
                crossover=[
                    Crossover(
                        from_component_id=consumer_name_to_id_map[crossover_stream.from_],
                        to_component_id=consumer_name_to_id_map[crossover_stream.to],
                        stream_name=crossover_stream.name,
                    )
                    for crossover_stream in self.component_conditions.crossover
                ]
                if self.component_conditions.crossover is not None
                else [],
            )
        else:
            component_conditions = SystemComponentConditions(
                crossover=[],
            )

        return dto.components.ConsumerSystem(
            component_type=self.component_type,
            name=self.name,
            user_defined_category=define_time_model_for_period(self.category, target_period=target_period),
            regularity=regularity,
            consumes=consumes,
            component_conditions=component_conditions,
            stream_conditions_priorities=self.stream_conditions_priorities,
            consumers=consumers,
            fuel=fuel,
        )
