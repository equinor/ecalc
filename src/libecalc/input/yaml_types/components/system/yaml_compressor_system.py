from datetime import datetime
from typing import Dict, List, Literal, Optional

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
from libecalc.input.yaml_types.yaml_stream import YamlStream
from pydantic import Field

opt_expr_list = Optional[List[ExpressionType]]


PriorityID = str
StreamID = str
ConsumerID = str

YamlConsumerStreamConditions = Dict[StreamID, YamlStream]
YamlConsumerStreamConditionsMap = Dict[ConsumerID, YamlConsumerStreamConditions]
YamlPriorities = Dict[PriorityID, YamlConsumerStreamConditionsMap]


class YamlCompressorSystem(YamlConsumerBase):
    class Config:
        title = "CompressorSystem"

    component_type: Literal[ComponentType.COMPRESSOR_SYSTEM_V2] = Field(
        ComponentType.COMPRESSOR_SYSTEM_V2,
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

    consumers: List[YamlCompressor]

    def to_dto(
        self,
        regularity: Dict[datetime, Expression],
        consumes: ConsumptionType,
        references: References,
        target_period: Period,
        fuel: Optional[Dict[datetime, dto.types.FuelType]] = None,
    ) -> dto.components.ConsumerSystem:
        compressors: List[dto.components.CompressorComponent] = [
            dto.components.CompressorComponent(
                consumes=consumes,
                regularity=regularity,
                name=compressor.name,
                user_defined_category=define_time_model_for_period(
                    compressor.category or self.category, target_period=target_period
                ),
                fuel=fuel,
                energy_usage_model={
                    timestep: resolve_and_validate_reference(
                        value=reference,
                        references=references.models,
                    )
                    for timestep, reference in define_time_model_for_period(
                        compressor.energy_usage_model, target_period=target_period
                    ).items()
                },
            )
            for compressor in self.consumers
        ]

        compressor_name_to_id_map = {compressor.name: compressor.id for compressor in compressors}

        if self.component_conditions is not None:
            component_conditions = SystemComponentConditions(
                crossover=[
                    Crossover(
                        from_component_id=compressor_name_to_id_map[crossover_stream.from_],
                        to_component_id=compressor_name_to_id_map[crossover_stream.to],
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
            component_type=ComponentType.COMPRESSOR_SYSTEM_V2,
            name=self.name,
            user_defined_category=define_time_model_for_period(self.category, target_period=target_period),
            regularity=regularity,
            consumes=consumes,
            component_conditions=component_conditions,
            stream_conditions_priorities=self.stream_conditions_priorities,
            consumers=compressors,
            fuel=fuel,
        )
