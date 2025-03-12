from typing import Literal

from libecalc.common.component_type import ComponentType
from libecalc.common.consumption_type import ConsumptionType
from libecalc.common.energy_usage_type import EnergyUsageType
from libecalc.common.string.string_utils import generate_id
from libecalc.common.temporal_model import TemporalModel
from libecalc.common.time_utils import Period
from libecalc.common.variables import ExpressionEvaluator
from libecalc.core.result import EcalcModelResult
from libecalc.core.result.emission import EmissionResult
from libecalc.domain.component_validation_error import (
    ComponentValidationException,
    ModelValidationError,
)
from libecalc.domain.energy import ComponentEnergyContext, Emitter, EnergyComponent, EnergyModel
from libecalc.domain.infrastructure.energy_components.fuel_model.fuel_model import FuelModel
from libecalc.domain.infrastructure.energy_components.legacy_consumer.component import (
    Consumer as ConsumerEnergyComponent,
)
from libecalc.domain.infrastructure.energy_components.legacy_consumer.consumer_function_mapper import EnergyModelMapper
from libecalc.domain.infrastructure.energy_components.utils import (
    _convert_keys_in_dictionary_from_str_to_periods,
    check_model_energy_usage_type,
)
from libecalc.domain.process.dto import FuelEnergyUsageModel
from libecalc.dto.fuel_type import FuelType
from libecalc.dto.types import ConsumerUserDefinedCategoryType
from libecalc.dto.utils.validators import validate_temporal_model
from libecalc.expression import Expression
from libecalc.presentation.yaml.validation_errors import Location


class FuelConsumer(Emitter, EnergyComponent):
    def __init__(
        self,
        name: str,
        regularity: dict[Period, Expression],
        user_defined_category: dict[Period, ConsumerUserDefinedCategoryType],
        component_type: Literal[
            ComponentType.COMPRESSOR,
            ComponentType.GENERIC,
            ComponentType.COMPRESSOR_SYSTEM,
        ],
        fuel: dict[Period, FuelType],
        energy_usage_model: dict[Period, FuelEnergyUsageModel],
        expression_evaluator: ExpressionEvaluator,
        consumes: Literal[ConsumptionType.FUEL] = ConsumptionType.FUEL,
    ):
        self.name = name
        self.regularity = self.check_regularity(regularity)
        validate_temporal_model(self.regularity)
        self.user_defined_category = user_defined_category
        self.energy_usage_model = self.check_energy_usage_model(energy_usage_model)
        self.expression_evaluator = expression_evaluator
        self.fuel = self.validate_fuel_exist(name=self.name, fuel=fuel, consumes=consumes)
        self._validate_fuel_consumer_temporal_models(self.energy_usage_model, self.fuel)
        self._check_model_energy_usage(self.energy_usage_model)
        self.consumes = consumes
        self.component_type = component_type
        self.consumer_results: dict[str, EcalcModelResult] = {}
        self.emission_results: dict[str, EmissionResult] | None = None

    @property
    def id(self) -> str:
        return generate_id(self.name)

    @staticmethod
    def check_regularity(regularity):
        if isinstance(regularity, dict) and len(regularity.values()) > 0:
            regularity = _convert_keys_in_dictionary_from_str_to_periods(regularity)
        return regularity

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

    def evaluate_energy_usage(self, context: ComponentEnergyContext) -> dict[str, EcalcModelResult]:
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
        self.consumer_results[self.id] = consumer.evaluate(expression_evaluator=self.expression_evaluator)
        return self.consumer_results

    def evaluate_emissions(
        self,
        energy_context: ComponentEnergyContext,
        energy_model: EnergyModel,
    ) -> dict[str, EmissionResult] | None:
        fuel_model = FuelModel(self.fuel)
        fuel_usage = energy_context.get_fuel_usage()

        assert fuel_usage is not None

        self.emission_results = fuel_model.evaluate_emissions(
            expression_evaluator=self.expression_evaluator,
            fuel_rate=fuel_usage.values,
        )

        return self.emission_results

    @staticmethod
    def check_energy_usage_model(energy_usage_model: dict[Period, FuelEnergyUsageModel]):
        """
        Make sure that temporal models are converted to Period objects if they are strings
        """
        if isinstance(energy_usage_model, dict) and len(energy_usage_model.values()) > 0:
            energy_usage_model = _convert_keys_in_dictionary_from_str_to_periods(energy_usage_model)
        return energy_usage_model

    @staticmethod
    def _validate_fuel_consumer_temporal_models(
        energy_usage_model: dict[Period, FuelEnergyUsageModel], fuel: dict[Period, FuelType]
    ):
        validate_temporal_model(energy_usage_model)
        validate_temporal_model(fuel)

    @staticmethod
    def _check_model_energy_usage(energy_usage_model: dict[Period, FuelEnergyUsageModel]):
        check_model_energy_usage_type(energy_usage_model, EnergyUsageType.FUEL)

    @classmethod
    def validate_fuel_exist(cls, name: str, fuel: dict[Period, FuelType] | None, consumes: ConsumptionType):
        """
        Make sure that temporal models are converted to Period objects if they are strings,
        and that fuel is set if consumption type is FUEL.
        """
        if isinstance(fuel, dict) and len(fuel.values()) > 0:
            fuel = _convert_keys_in_dictionary_from_str_to_periods(fuel)
        if consumes == ConsumptionType.FUEL and (fuel is None or len(fuel) < 1):
            msg = "Missing fuel for fuel consumer"
            raise ComponentValidationException(
                errors=[
                    ModelValidationError(
                        name=name,
                        location=Location([name]),  # for now, we will use the name as the location
                        message=str(msg),
                    )
                ],
            )
        return fuel
