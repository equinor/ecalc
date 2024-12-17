from typing import Literal

from libecalc.application.energy.component_energy_context import ComponentEnergyContext
from libecalc.application.energy.energy_component import EnergyComponent
from libecalc.common.component_type import ComponentType
from libecalc.common.consumption_type import ConsumptionType
from libecalc.common.energy_usage_type import EnergyUsageType
from libecalc.common.temporal_model import TemporalModel
from libecalc.common.time_utils import Period
from libecalc.common.variables import ExpressionEvaluator
from libecalc.core.result import EcalcModelResult
from libecalc.domain.infrastructure.energy_components.base.component_dto import BaseConsumer
from libecalc.domain.infrastructure.energy_components.legacy_consumer.component import (
    Consumer as ConsumerEnergyComponent,
)
from libecalc.domain.infrastructure.energy_components.legacy_consumer.consumer_function_mapper import EnergyModelMapper
from libecalc.domain.infrastructure.energy_components.utils import (
    _convert_keys_in_dictionary_from_str_to_periods,
    check_model_energy_usage_type,
)
from libecalc.dto.models import ElectricEnergyUsageModel
from libecalc.dto.types import ConsumerUserDefinedCategoryType
from libecalc.dto.utils.validators import validate_temporal_model
from libecalc.expression import Expression


class ElectricityConsumer(BaseConsumer, EnergyComponent):
    def __init__(
        self,
        name: str,
        regularity: dict[Period, Expression],
        user_defined_category: dict[Period, ConsumerUserDefinedCategoryType],
        component_type: Literal[
            ComponentType.COMPRESSOR,
            ComponentType.PUMP,
            ComponentType.GENERIC,
            ComponentType.PUMP_SYSTEM,
            ComponentType.COMPRESSOR_SYSTEM,
        ],
        energy_usage_model: dict[Period, ElectricEnergyUsageModel],
        consumes: Literal[ConsumptionType.ELECTRICITY] = ConsumptionType.ELECTRICITY,
    ):
        super().__init__(name, regularity, consumes, user_defined_category, component_type, energy_usage_model, None)
        self.energy_usage_model = self.check_energy_usage_model(energy_usage_model)
        self._validate_el_consumer_temporal_model(self.energy_usage_model)
        self._check_model_energy_usage(self.energy_usage_model)

    def is_fuel_consumer(self) -> bool:
        return False

    def is_electricity_consumer(self) -> bool:
        return True

    def is_provider(self) -> bool:
        return False

    def is_container(self) -> bool:
        return False

    def get_component_process_type(self) -> ComponentType:
        return self.component_type

    def get_name(self) -> str:
        return self.name

    def evaluate_energy_usage(
        self, expression_evaluator: ExpressionEvaluator, context: ComponentEnergyContext
    ) -> dict[str, EcalcModelResult]:
        consumer_results: dict[str, EcalcModelResult] = {}
        consumer = ConsumerEnergyComponent(
            id=self.id,
            name=self.name,
            component_type=self.component_type,
            regularity=TemporalModel(self.regularity),
            consumes=self.consumes,
            energy_usage_model=TemporalModel(
                {
                    period: EnergyModelMapper.from_dto_to_domain(model)
                    for period, model in self.energy_usage_model.items()
                }
            ),
        )
        consumer_results[self.id] = consumer.evaluate(expression_evaluator=expression_evaluator)

        return consumer_results

    @staticmethod
    def check_energy_usage_model(energy_usage_model: dict[Period, ElectricEnergyUsageModel]):
        """
        Make sure that temporal models are converted to Period objects if they are strings
        """
        if isinstance(energy_usage_model, dict) and len(energy_usage_model.values()) > 0:
            energy_usage_model = _convert_keys_in_dictionary_from_str_to_periods(energy_usage_model)
        return energy_usage_model

    @staticmethod
    def _validate_el_consumer_temporal_model(energy_usage_model: dict[Period, ElectricEnergyUsageModel]):
        validate_temporal_model(energy_usage_model)

    @staticmethod
    def _check_model_energy_usage(energy_usage_model: dict[Period, ElectricEnergyUsageModel]):
        check_model_energy_usage_type(energy_usage_model, EnergyUsageType.POWER)
