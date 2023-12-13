from datetime import datetime
from typing import Dict, Literal, Optional

from pydantic import Field

from libecalc import dto
from libecalc.common.time_utils import Period, define_time_model_for_period
from libecalc.core.consumers.factory import create_consumer
from libecalc.core.consumers.pump import Pump
from libecalc.dto.base import ComponentType
from libecalc.dto.components import PumpComponent
from libecalc.dto.types import ConsumptionType
from libecalc.expression import Expression
from libecalc.presentation.yaml.mappers.utils import resolve_reference
from libecalc.presentation.yaml.yaml_entities import References
from libecalc.presentation.yaml.yaml_types.components.yaml_base import (
    YamlConsumerBase,
)
from libecalc.presentation.yaml.yaml_types.yaml_temporal_model import YamlTemporalModel


class YamlPump(YamlConsumerBase):
    class Config:
        title = "Pump"

    component_type: Literal[ComponentType.PUMP_V2] = Field(
        ...,
        title="TYPE",
        description="The type of the component",
        alias="TYPE",
    )

    energy_usage_model: YamlTemporalModel[str]

    def to_dto(
        self,
        consumes: ConsumptionType,
        regularity: Dict[datetime, Expression],
        target_period: Period,
        references: References,
        category: str,
        fuel: Optional[Dict[datetime, dto.types.FuelType]],
    ) -> PumpComponent:
        return PumpComponent(
            consumes=consumes,
            regularity=regularity,
            name=self.name,
            user_defined_category=define_time_model_for_period(self.category or category, target_period=target_period),
            fuel=fuel,
            energy_usage_model={
                timestep: resolve_reference(
                    value=reference,
                    references=references.models,
                )
                for timestep, reference in define_time_model_for_period(
                    self.energy_usage_model, target_period=target_period
                ).items()
            },
        )

    def to_domain(
        self,
        consumes: ConsumptionType,  # important in network, ie producer/consumer and units etc
        regularity: Dict[datetime, Expression],  # skip, already converted to stream_day ...
        target_period: Period,  # what is this needed for? to get the correct model for a given timestep
        references: References,  # need to resolve, but that should be handled "before"? or here?
        category: str,  # meta
        fuel: Optional[Dict[datetime, dto.types.FuelType]],
    ) -> Pump:  # also, not relevant for domain, handled "above"?
        # Remove this intermediate step ...
        dto = PumpComponent(
            consumes=consumes,
            regularity=regularity,
            name=self.name,
            user_defined_category=define_time_model_for_period(self.category or category, target_period=target_period),
            fuel=fuel,
            energy_usage_model={
                timestep: resolve_reference(
                    value=reference,
                    references=references.models,
                )
                for timestep, reference in define_time_model_for_period(
                    self.energy_usage_model, target_period=target_period
                ).items()
            },
        )

        return create_consumer(consumer=dto, timestep=datetime.now())
