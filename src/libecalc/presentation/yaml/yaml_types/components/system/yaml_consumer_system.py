from datetime import datetime
from typing import Annotated, Generic, Literal, Optional, TypeVar, Union

from pydantic import ConfigDict, Field, TypeAdapter

from libecalc.common.component_type import ComponentType
from libecalc.common.consumption_type import ConsumptionType
from libecalc.common.time_utils import Period, define_time_model_for_period
from libecalc.domain.infrastructure.energy_components.base.component_dto import Crossover, SystemComponentConditions
from libecalc.domain.infrastructure.energy_components.consumer_system.consumer_system_dto import ConsumerSystem
from libecalc.dto import FuelType
from libecalc.expression import Expression
from libecalc.presentation.yaml.domain.reference_service import ReferenceService
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
from libecalc.presentation.yaml.yaml_types.components.yaml_expression_type import (
    YamlExpressionType,
)
from libecalc.presentation.yaml.yaml_types.components.yaml_pump import YamlPump
from libecalc.presentation.yaml.yaml_types.yaml_stream_conditions import (
    YamlStreamConditions,
)

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

    def to_dto(
        self,
        regularity: dict[datetime, Expression],
        consumes: ConsumptionType,
        references: ReferenceService,
        target_period: Period,
        fuel: Optional[dict[datetime, FuelType]] = None,
    ) -> ConsumerSystem:
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

        return ConsumerSystem(
            component_type=self.component_type,
            name=self.name,
            user_defined_category=define_time_model_for_period(self.category, target_period=target_period),
            regularity=regularity,
            consumes=consumes,
            component_conditions=component_conditions,
            stream_conditions_priorities=TypeAdapter(YamlPriorities).dump_python(
                self.stream_conditions_priorities
            ),  # TODO: unnecessary, but we should remove the need to have dto here (two very similar classes)
            consumers=consumers,
            fuel=fuel,
        )
