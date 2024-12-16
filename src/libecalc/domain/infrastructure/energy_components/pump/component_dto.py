from typing import Literal

from libecalc.application.energy.energy_component import EnergyComponent
from libecalc.common.component_type import ComponentType
from libecalc.common.consumption_type import ConsumptionType
from libecalc.common.time_utils import Period
from libecalc.domain.infrastructure.energy_components.base.component_dto import BaseConsumer
from libecalc.dto.models.pump import PumpModel


class PumpComponent(BaseConsumer, EnergyComponent):
    component_type: Literal[ComponentType.PUMP] = ComponentType.PUMP
    energy_usage_model: dict[Period, PumpModel]

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
