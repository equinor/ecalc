from typing import Literal, Optional

from pydantic import field_validator
from pydantic_core.core_schema import ValidationInfo

from libecalc.application.energy.component_energy_context import ComponentEnergyContext
from libecalc.application.energy.emitter import Emitter
from libecalc.application.energy.energy_component import EnergyComponent
from libecalc.application.energy.energy_model import EnergyModel
from libecalc.common.component_type import ComponentType
from libecalc.common.consumption_type import ConsumptionType
from libecalc.common.energy_usage_type import EnergyUsageType
from libecalc.common.temporal_model import TemporalModel
from libecalc.common.time_utils import Period
from libecalc.common.variables import ExpressionEvaluator
from libecalc.core.result import EcalcModelResult
from libecalc.core.result.emission import EmissionResult
from libecalc.domain.infrastructure.energy_components.base.component_dto import BaseConsumer
from libecalc.domain.infrastructure.energy_components.fuel_model.fuel_model import FuelModel
from libecalc.domain.infrastructure.energy_components.legacy_consumer.component import (
    Consumer as ConsumerEnergyComponent,
)
from libecalc.domain.infrastructure.energy_components.legacy_consumer.consumer_function_mapper import EnergyModelMapper
from libecalc.domain.infrastructure.energy_components.utils import (
    _convert_keys_in_dictionary_from_str_to_periods,
    check_model_energy_usage_type,
)
from libecalc.dto.fuel_type import FuelType
from libecalc.dto.models import FuelEnergyUsageModel
from libecalc.dto.utils.validators import validate_temporal_model


class FuelConsumer(BaseConsumer, Emitter, EnergyComponent):
    component_type: Literal[
        ComponentType.COMPRESSOR,
        ComponentType.GENERIC,
        ComponentType.COMPRESSOR_SYSTEM,
    ]
    consumes: Literal[ConsumptionType.FUEL] = ConsumptionType.FUEL
    fuel: dict[Period, FuelType]
    energy_usage_model: dict[Period, FuelEnergyUsageModel]

    _validate_fuel_consumer_temporal_models = field_validator("energy_usage_model", "fuel")(validate_temporal_model)
    _check_model_energy_usage = field_validator("energy_usage_model")(
        lambda data: check_model_energy_usage_type(data, EnergyUsageType.FUEL)
    )

    def is_fuel_consumer(self) -> bool:
        return True

    def is_electricity_consumer(self) -> bool:
        return False

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

    def evaluate_emissions(
        self,
        energy_context: ComponentEnergyContext,
        energy_model: EnergyModel,
        expression_evaluator: ExpressionEvaluator,
    ) -> Optional[dict[str, EmissionResult]]:
        fuel_model = FuelModel(self.fuel)
        fuel_usage = energy_context.get_fuel_usage()

        assert fuel_usage is not None

        return fuel_model.evaluate_emissions(
            expression_evaluator=expression_evaluator,
            fuel_rate=fuel_usage.values,
        )

    @field_validator("energy_usage_model", mode="before")
    @classmethod
    def check_energy_usage_model(cls, energy_usage_model, info: ValidationInfo):
        """
        Make sure that temporal models are converted to Period objects if they are strings
        """
        if isinstance(energy_usage_model, dict) and len(energy_usage_model.values()) > 0:
            energy_usage_model = _convert_keys_in_dictionary_from_str_to_periods(energy_usage_model)
        return energy_usage_model

    @field_validator("fuel", mode="before")
    @classmethod
    def check_fuel(cls, fuel):
        """
        Make sure that temporal models are converted to Period objects if they are strings
        """
        if isinstance(fuel, dict) and len(fuel.values()) > 0:
            fuel = _convert_keys_in_dictionary_from_str_to_periods(fuel)
        return fuel
