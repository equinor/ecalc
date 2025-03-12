from typing import Literal

from libecalc.common.component_type import ComponentType
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
from libecalc.domain.infrastructure.energy_components.electricity_consumer.electricity_consumer import (
    ElectricityConsumer,
)
from libecalc.domain.infrastructure.energy_components.fuel_consumer.fuel_consumer import FuelConsumer
from libecalc.domain.infrastructure.energy_components.fuel_model.fuel_model import FuelModel
from libecalc.domain.infrastructure.energy_components.generator_set.generator_set import Genset
from libecalc.domain.infrastructure.energy_components.utils import _convert_keys_in_dictionary_from_str_to_periods
from libecalc.domain.process.core.generator import GeneratorModelSampled
from libecalc.domain.process.dto import GeneratorSetSampled
from libecalc.dto.component_graph import ComponentGraph
from libecalc.dto.fuel_type import FuelType
from libecalc.dto.types import ConsumerUserDefinedCategoryType
from libecalc.dto.utils.validators import (
    ExpressionType,
    validate_temporal_model,
)
from libecalc.expression import Expression
from libecalc.presentation.yaml.validation_errors import Location


class GeneratorSet(Emitter, EnergyComponent):
    def __init__(
        self,
        name: str,
        user_defined_category: dict[Period, ConsumerUserDefinedCategoryType],
        generator_set_model: dict[Period, GeneratorSetSampled],
        regularity: dict[Period, Expression],
        expression_evaluator: ExpressionEvaluator,
        consumers: list[ElectricityConsumer] = None,
        fuel: dict[Period, FuelType] = None,
        cable_loss: ExpressionType | None = None,
        max_usage_from_shore: ExpressionType | None = None,
        component_type: Literal[ComponentType.GENERATOR_SET] = ComponentType.GENERATOR_SET,
    ):
        self.name = name
        self.user_defined_category = user_defined_category
        self.regularity = self.check_regularity(regularity)
        self.expression_evaluator = expression_evaluator
        validate_temporal_model(self.regularity)
        self.generator_set_model = self.check_generator_set_model(generator_set_model)
        self.fuel = self.check_fuel(fuel)
        self.consumers = consumers if consumers is not None else []
        self.cable_loss = cable_loss
        self.max_usage_from_shore = max_usage_from_shore
        self.component_type = component_type
        self._validate_genset_temporal_models(self.generator_set_model, self.fuel)
        self.check_consumers()
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
        return True

    def is_container(self) -> bool:
        return False

    def get_component_process_type(self) -> ComponentType:
        return self.component_type

    def get_name(self) -> str:
        return self.name

    def evaluate_energy_usage(self, context: ComponentEnergyContext) -> dict[str, EcalcModelResult]:
        fuel_consumer = Genset(
            id=self.id,
            name=self.name,
            temporal_generator_set_model=TemporalModel(
                {
                    period: GeneratorModelSampled(
                        fuel_values=model.fuel_values,
                        power_values=model.power_values,
                        energy_usage_adjustment_constant=model.energy_usage_adjustment_constant,
                        energy_usage_adjustment_factor=model.energy_usage_adjustment_factor,
                    )
                    for period, model in self.generator_set_model.items()
                }
            ),
        )

        self.consumer_results[self.id] = EcalcModelResult(
            component_result=fuel_consumer.evaluate(
                expression_evaluator=self.expression_evaluator,
                power_requirement=context.get_power_requirement(),
            ),
            models=[],
            sub_components=[],
        )

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
    def _validate_genset_temporal_models(
        generator_set_model: dict[Period, GeneratorSetSampled], fuel: dict[Period, FuelType]
    ):
        validate_temporal_model(generator_set_model)
        validate_temporal_model(fuel)

    @staticmethod
    def check_generator_set_model(generator_set_model: dict[Period, GeneratorSetSampled]):
        if isinstance(generator_set_model, dict) and len(generator_set_model.values()) > 0:
            generator_set_model = _convert_keys_in_dictionary_from_str_to_periods(generator_set_model)
        return generator_set_model

    def check_fuel(self, fuel: dict[Period, FuelType]):
        """
        Make sure that temporal models are converted to Period objects if they are strings,
        and that fuel is set
        """
        if isinstance(fuel, dict) and len(fuel.values()) > 0:
            fuel = _convert_keys_in_dictionary_from_str_to_periods(fuel)
        if self.is_fuel_consumer() and (fuel is None or len(fuel) < 1):
            msg = "Missing fuel for generator set"
            raise ComponentValidationException(
                errors=[
                    ModelValidationError(
                        name=self.name,
                        location=Location([self.name]),  # for now, we will use the name as the location
                        message=str(msg),
                    )
                ],
            )
        return fuel

    def check_consumers(self):
        errors: list[ModelValidationError] = []
        for consumer in self.consumers:
            if isinstance(consumer, FuelConsumer):
                errors.append(
                    ModelValidationError(
                        name=consumer.name,
                        message="The consumer is not an electricity consumer. "
                        "Generators can not have fuel consumers.",
                    )
                )

        if errors:
            raise ComponentValidationException(errors=errors)

    def get_graph(self) -> ComponentGraph:
        graph = ComponentGraph()
        graph.add_node(self)
        for electricity_consumer in self.consumers:
            if hasattr(electricity_consumer, "get_graph"):
                graph.add_subgraph(electricity_consumer.get_graph())
            else:
                graph.add_node(electricity_consumer)

            graph.add_edge(self.id, electricity_consumer.id)

        return graph
