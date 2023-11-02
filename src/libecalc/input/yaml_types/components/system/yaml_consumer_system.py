from datetime import datetime
from typing import Dict, List, Literal, Optional, Union

from libecalc import dto
from libecalc.common.time_utils import Period, define_time_model_for_period
from libecalc.dto.base import ComponentType
from libecalc.dto.components import Crossover, SystemComponentConditions
from libecalc.dto.types import ConsumptionType
from libecalc.expression import Expression
from libecalc.expression.expression import ExpressionType
from libecalc.input.mappers.utils import resolve_and_validate_reference
from libecalc.input.yaml_entities import References
from libecalc.input.yaml_types.components.system.yaml_system_component_conditions import (
    YamlSystemComponentConditions,
)
from libecalc.input.yaml_types.components.yaml_base import (
    YamlConsumerBase,
)
from libecalc.input.yaml_types.components.yaml_compressor import YamlCompressor
from libecalc.input.yaml_types.components.yaml_pump import YamlPump
from libecalc.input.yaml_types.yaml_stream import YamlStream
from pydantic import Field

opt_expr_list = Optional[List[ExpressionType]]

PriorityID = str
StreamID = str
ConsumerID = str

YamlConsumerStreamConditions = Dict[StreamID, YamlStream]
YamlConsumerStreamConditionsMap = Dict[ConsumerID, YamlConsumerStreamConditions]
YamlPriorities = Dict[PriorityID, YamlConsumerStreamConditionsMap]


def map_consumer(
    consumer: Union[YamlPump, YamlCompressor],
    consumes: ConsumptionType,
    regularity: Dict[datetime, Expression],
    category: str,
    target_period: Period,
    references: References,
    fuel: Optional[Dict[datetime, dto.types.FuelType]],
):
    if consumer.component_type == ComponentType.COMPRESSOR:
        return dto.components.CompressorComponent(
            consumes=consumes,
            regularity=regularity,
            name=consumer.name,
            user_defined_category=define_time_model_for_period(
                consumer.category or category, target_period=target_period
            ),
            fuel=fuel,
            energy_usage_model={
                timestep: resolve_and_validate_reference(
                    value=reference,
                    references=references.models,
                )
                for timestep, reference in define_time_model_for_period(
                    consumer.energy_usage_model, target_period=target_period
                ).items()
            },
        )
    elif consumer.component_type == ComponentType.PUMP:
        return dto.components.PumpComponent(
            consumes=consumes,
            regularity=regularity,
            name=consumer.name,
            user_defined_category=define_time_model_for_period(
                consumer.category or category, target_period=target_period
            ),
            fuel=fuel,
            energy_usage_model={
                timestep: resolve_and_validate_reference(
                    value=reference,
                    references=references.models,
                )
                for timestep, reference in define_time_model_for_period(
                    consumer.energy_usage_model, target_period=target_period
                ).items()
            },
        )
    else:
        raise ValueError("Unknown consumer type")


class YamlConsumerSystem(YamlConsumerBase):
    class Config:
        title = "ConsumerSystem"

    component_type: Literal[ComponentType.COMPRESSOR_SYSTEM_V2, ComponentType.PUMP_SYSTEM_V2] = Field(
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

    consumers: List[Union[YamlCompressor, YamlPump]]

    def to_dto(
        self,
        regularity: Dict[datetime, Expression],
        consumes: ConsumptionType,
        references: References,
        target_period: Period,
        fuel: Optional[Dict[datetime, dto.types.FuelType]] = None,
    ) -> dto.components.ConsumerSystem:
        consumers = [
            map_consumer(
                consumer,
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
