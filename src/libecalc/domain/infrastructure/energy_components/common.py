from typing import Literal, Optional, TypeVar, Union

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
from libecalc.expression import Expression

Consumer = Union[FuelConsumer, ElectricityConsumer]

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


class CompressorOperationalSettings:
    def __init__(self, rate: Expression, inlet_pressure: Expression, outlet_pressure: Expression):
        self.rate = rate
        self.inlet_pressure = inlet_pressure
        self.outlet_pressure = outlet_pressure


class PumpOperationalSettings:
    def __init__(
        self, rate: Expression, inlet_pressure: Expression, outlet_pressure: Expression, fluid_density: Expression
    ):
        self.rate = rate
        self.inlet_pressure = inlet_pressure
        self.outlet_pressure = outlet_pressure
        self.fluid_density = fluid_density


class Stream:
    def __init__(self, from_component_id: str, to_component_id: str, stream_name: Optional[str] = None):
        self.stream_name = stream_name
        self.from_component_id = from_component_id
        self.to_component_id = to_component_id


ConsumerComponent = TypeVar("ConsumerComponent", bound=Union[CompressorComponent, PumpComponent])


class TrainComponent(BaseConsumer):
    component_type: Literal[ComponentType.TRAIN_V2] = ComponentType.TRAIN_V2

    def __init__(
        self,
        name: str,
        regularity: dict,
        consumes,
        user_defined_category: dict,
        component_type: ComponentType,
        stages: list,
        streams: list,
    ):
        super().__init__(name, regularity, consumes, user_defined_category, component_type)
        self.stages = stages
        self.streams = streams
