from typing import Annotated, Literal, Optional, Union

from pydantic import ConfigDict, Field

from libecalc.common.component_type import ComponentType
from libecalc.common.consumption_type import ConsumptionType
from libecalc.common.time_utils import Period
from libecalc.common.variables import ExpressionEvaluator
from libecalc.domain.infrastructure.energy_components.compressor.component_dto import CompressorComponent
from libecalc.domain.infrastructure.energy_components.consumer_system.consumer_system_dto import ConsumerSystem
from libecalc.domain.infrastructure.energy_components.pump.component_dto import PumpComponent
from libecalc.dto import FuelType
from libecalc.expression import Expression
from libecalc.presentation.yaml.domain.reference_service import ReferenceService
from libecalc.presentation.yaml.yaml_types.components.system import yaml_priorities
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

    stream_conditions_priorities: yaml_priorities.YamlPriorities = Field(
        ...,
        title="Stream conditions priorities",
        description="A list of prioritised stream conditions per consumer.",
    )

    consumers: list[Annotated[TYamlConsumer, Field(discriminator="component_type")]]

    def to_dto(
        self,
        regularity: dict[Period, Expression],
        consumes: ConsumptionType,
        expression_evaluator: ExpressionEvaluator,
        references: ReferenceService,
        target_period: Period,
        fuel: Optional[dict[Period, FuelType]],
    ) -> ConsumerSystem:
        common_vars = self._get_common_variables(regularity, consumes, references, target_period, fuel)
        consumers = self.to_dto_consumers(**common_vars)
        consumer_name_to_id_map = {consumer.name: consumer.id for consumer in consumers}  # When done in the

        return ConsumerSystem(
            name=self.name,
            user_defined_category=self.category,
            regularity=regularity,
            consumes=consumes,
            component_conditions=self.component_conditions.to_dto(consumer_name_to_id_map),
            priorities=yaml_priorities.to_dto(self.stream_conditions_priorities),
            consumers=consumers,
            expression_evaluator=expression_evaluator,
            references=references,
            target_period=target_period,
            fuel=fuel,
            component_type=ComponentType.CONSUMER_SYSTEM_V2,
        )

    def to_dto_consumers(self, **kwargs) -> Union[list[CompressorComponent], list[PumpComponent]]:
        return [consumer.to_dto(**kwargs) for consumer in self.consumers]

    def _get_common_variables(
        self,
        regularity: dict[Period, Expression],
        consumes: ConsumptionType,
        references: ReferenceService,
        target_period: Period,
        fuel: Optional[dict[Period, FuelType]],
    ) -> dict:
        return {
            "regularity": regularity,
            "consumes": consumes,
            "references": references,
            "target_period": target_period,
            "fuel": fuel,
            "category": self.category,
        }
