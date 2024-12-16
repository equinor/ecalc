from typing import Annotated, Literal, Optional, TypeVar, Union

from pydantic import ConfigDict, Field

from libecalc.common.component_type import ComponentType
from libecalc.domain.infrastructure.energy_components.asset.asset import Asset
from libecalc.domain.infrastructure.energy_components.base.component_dto import BaseConsumer
from libecalc.domain.infrastructure.energy_components.compressor.component_dto import CompressorComponent
from libecalc.domain.infrastructure.energy_components.consumer_system.consumer_system_dto import ConsumerSystem
from libecalc.domain.infrastructure.energy_components.electricity_consumer.electricity_consumer import (
    ElectricityConsumer,
)
from libecalc.domain.infrastructure.energy_components.fuel_consumer.fuel_consumer import FuelConsumer
from libecalc.domain.infrastructure.energy_components.generator_set.generator_set_dto import GeneratorSet
from libecalc.domain.infrastructure.energy_components.installation.installation import Installation
from libecalc.domain.infrastructure.energy_components.pump.component_dto import PumpComponent
from libecalc.dto.base import EcalcBaseModel
from libecalc.expression import Expression

Consumer = Annotated[Union[FuelConsumer, ElectricityConsumer], Field(discriminator="consumes")]

ComponentDTO = Union[
    Asset,
    Installation,
    GeneratorSet,
    FuelConsumer,
    ElectricityConsumer,
    ConsumerSystem,
    CompressorComponent,
    PumpComponent,
]


class CompressorOperationalSettings(EcalcBaseModel):
    rate: Expression
    inlet_pressure: Expression
    outlet_pressure: Expression


class PumpOperationalSettings(EcalcBaseModel):
    rate: Expression
    inlet_pressure: Expression
    outlet_pressure: Expression
    fluid_density: Expression


class Stream(EcalcBaseModel):
    model_config = ConfigDict(populate_by_name=True)

    stream_name: Optional[str] = Field(None)
    from_component_id: str
    to_component_id: str


ConsumerComponent = TypeVar("ConsumerComponent", bound=Union[CompressorComponent, PumpComponent])


class TrainComponent(BaseConsumer):
    component_type: Literal[ComponentType.TRAIN_V2] = Field(
        ComponentType.TRAIN_V2,
        title="TYPE",
        description="The type of the component",
        alias="TYPE",
    )
    stages: list[ConsumerComponent]
    streams: list[Stream]
