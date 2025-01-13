from typing import Literal, Optional, TypeVar, Union

from libecalc.common.component_type import ComponentType
from libecalc.common.consumption_type import ConsumptionType
from libecalc.common.string.string_utils import generate_id
from libecalc.common.time_utils import Period
from libecalc.domain.infrastructure.energy_components.asset.asset import Asset
from libecalc.domain.infrastructure.energy_components.compressor.component_dto import CompressorComponent
from libecalc.domain.infrastructure.energy_components.consumer_system.consumer_system_dto import ConsumerSystem
from libecalc.domain.infrastructure.energy_components.electricity_consumer.electricity_consumer import (
    ElectricityConsumer,
)
from libecalc.domain.infrastructure.energy_components.fuel_consumer.fuel_consumer import FuelConsumer
from libecalc.domain.infrastructure.energy_components.generator_set.generator_set_dto import GeneratorSet
from libecalc.domain.infrastructure.energy_components.installation.installation import Installation
from libecalc.domain.infrastructure.energy_components.pump.component_dto import PumpComponent
from libecalc.domain.infrastructure.energy_components.utils import _convert_keys_in_dictionary_from_str_to_periods
from libecalc.dto.utils.validators import validate_temporal_model
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


class TrainComponent:
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
        self.name = name
        self.regularity = self.check_regularity(regularity)
        validate_temporal_model(self.regularity)
        self.consumes = consumes
        self.user_defined_category = user_defined_category
        self.component_type = component_type
        self.stages = stages
        self.streams = streams

    @property
    def id(self) -> str:
        return generate_id(self.name)

    @staticmethod
    def check_regularity(regularity: dict[Period, Expression]):
        if isinstance(regularity, dict) and len(regularity.values()) > 0:
            regularity = _convert_keys_in_dictionary_from_str_to_periods(regularity)
        return regularity

    def is_fuel_consumer(self) -> bool:
        return self.consumes == ConsumptionType.FUEL

    def is_electricity_consumer(self) -> bool:
        return self.consumes == ConsumptionType.ELECTRICITY

    def is_provider(self) -> bool:
        return False

    def is_container(self) -> bool:
        return False

    def get_component_process_type(self) -> ComponentType:
        return self.component_type

    def get_name(self) -> str:
        return self.name
