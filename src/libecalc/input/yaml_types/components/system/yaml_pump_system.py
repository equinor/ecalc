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
from libecalc.input.yaml_types.components.system.yaml_compressor_system import (
    YamlPriorities,
)
from libecalc.input.yaml_types.components.system.yaml_system_component_conditions import (
    YamlSystemComponentConditions,
)
from libecalc.input.yaml_types.components.yaml_base import (
    YamlConsumerBase,
)
from libecalc.input.yaml_types.components.yaml_pump import YamlPump
from pydantic import Field

opt_expr_list = Optional[List[ExpressionType]]


class YamlPumpSystem(YamlConsumerBase):
    class Config:
        title = "PumpSystem"

    component_type: Literal[ComponentType.PUMP_SYSTEM_V2] = Field(
        ComponentType.PUMP_SYSTEM_V2,
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

    consumers: List[YamlPump]

    def to_dto(
        self,
        regularity: Dict[datetime, Expression],
        consumes: ConsumptionType,
        references: References,
        target_period: Period,
        fuel: Optional[Dict[datetime, dto.types.FuelType]] = None,
    ) -> dto.components.ConsumerSystem:
        pumps: List[dto.components.PumpComponent] = [
            dto.components.PumpComponent(
                consumes=consumes,
                regularity=regularity,
                name=pump.name,
                user_defined_category=define_time_model_for_period(
                    pump.category or self.category, target_period=target_period
                ),
                fuel=fuel,
                energy_usage_model={
                    timestep: resolve_and_validate_reference(
                        value=reference,
                        references=references.models,
                    )
                    for timestep, reference in define_time_model_for_period(
                        pump.energy_usage_model, target_period=target_period
                    ).items()
                },
            )
            for pump in self.consumers
        ]

        pump_name_to_id_map = {pump.name: pump.id for pump in pumps}

        if self.component_conditions is not None:
            component_conditions = SystemComponentConditions(
                crossover=[
                    Crossover(
                        from_component_id=pump_name_to_id_map[crossover_stream.from_],
                        to_component_id=pump_name_to_id_map[crossover_stream.to],
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
            component_type=ComponentType.PUMP_SYSTEM_V2,
            name=self.name,
            user_defined_category=define_time_model_for_period(self.category, target_period=target_period),
            regularity=regularity,
            consumes=consumes,
            component_conditions=component_conditions,
            stream_conditions_priorities=self.stream_conditions_priorities,
            consumers=pumps,
            fuel=fuel,
        )
