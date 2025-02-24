from collections import defaultdict
from typing import Literal, Optional, Union

from libecalc.common.component_type import ComponentType
from libecalc.common.consumption_type import ConsumptionType
from libecalc.common.priority_optimizer import PriorityOptimizer
from libecalc.common.stream_conditions import TimeSeriesStreamConditions
from libecalc.common.string.string_utils import generate_id
from libecalc.common.time_utils import Period
from libecalc.common.units import Unit
from libecalc.common.utils.rates import (
    TimeSeriesFloat,
    TimeSeriesInt,
    TimeSeriesStreamDayRate,
    TimeSeriesString,
)
from libecalc.common.variables import ExpressionEvaluator
from libecalc.core.result import ComponentResult, EcalcModelResult
from libecalc.core.result.emission import EmissionResult
from libecalc.domain.energy import ComponentEnergyContext, Emitter, EnergyComponent, EnergyModel
from libecalc.domain.infrastructure.energy_components.base.component_dto import (
    ConsumerID,
    Priorities,
    PriorityID,
    SystemComponentConditions,
    SystemStreamConditions,
)
from libecalc.domain.infrastructure.energy_components.component_validation_error import (
    ComponentValidationException,
    ModelValidationError,
)
from libecalc.domain.infrastructure.energy_components.compressor import Compressor
from libecalc.domain.infrastructure.energy_components.compressor.component_dto import CompressorComponent
from libecalc.domain.infrastructure.energy_components.consumer_system.consumer_system import (
    ConsumerSystem as ConsumerSystemEnergyComponent,
)
from libecalc.domain.infrastructure.energy_components.fuel_model.fuel_model import FuelModel
from libecalc.domain.infrastructure.energy_components.pump import Pump
from libecalc.domain.infrastructure.energy_components.pump.component_dto import PumpComponent
from libecalc.domain.infrastructure.energy_components.utils import _convert_keys_in_dictionary_from_str_to_periods
from libecalc.domain.process.core.compressor import create_compressor_model
from libecalc.domain.process.core.pump import create_pump_model
from libecalc.dto import FuelType
from libecalc.dto.component_graph import ComponentGraph
from libecalc.dto.types import ConsumerUserDefinedCategoryType
from libecalc.dto.utils.validators import validate_temporal_model
from libecalc.expression import Expression


class ConsumerSystem(Emitter, EnergyComponent):
    def __init__(
        self,
        name: str,
        user_defined_category: dict[Period, ConsumerUserDefinedCategoryType],
        regularity: dict[Period, Expression],
        consumes: ConsumptionType,
        component_conditions: Optional[SystemComponentConditions],
        priorities: Priorities[SystemStreamConditions],
        consumers: Union[list[CompressorComponent], list[PumpComponent]],
        expression_evaluator: ExpressionEvaluator,
        target_period: Period,
        fuel: Optional[dict[Period, FuelType]] = None,
        component_type: Literal[ComponentType.CONSUMER_SYSTEM_V2] = ComponentType.CONSUMER_SYSTEM_V2,
    ):
        self.name = name
        self.user_defined_category = user_defined_category
        self.regularity = self.check_regularity(regularity)
        self.consumes = consumes
        validate_temporal_model(self.regularity)
        self.component_conditions = component_conditions
        self.stream_conditions_priorities = priorities
        self.expression_evaluator = expression_evaluator
        self.target_period = target_period
        self.fuel = self.validate_fuel_exist(name=self.name, fuel=fuel, consumes=consumes)
        self.component_type = component_type
        self.consumers = consumers
        self.consumer_results: dict[str, EcalcModelResult] = {}
        self.emission_results: Optional[dict[str, EmissionResult]] = None

    @property
    def id(self) -> str:
        return generate_id(self.name)

    @staticmethod
    def check_regularity(regularity):
        if isinstance(regularity, dict) and len(regularity.values()) > 0:
            regularity = _convert_keys_in_dictionary_from_str_to_periods(regularity)
        return regularity

    @staticmethod
    def validate_fuel_exist(name: str, fuel: Optional[dict[Period, FuelType]], consumes: ConsumptionType):
        if isinstance(fuel, dict) and len(fuel.values()) > 0:
            fuel = _convert_keys_in_dictionary_from_str_to_periods(fuel)
        if consumes == ConsumptionType.FUEL and (fuel is None or len(fuel) < 1):
            msg = "Missing fuel for fuel consumer"
            raise ComponentValidationException(
                errors=[
                    ModelValidationError(
                        name=name,
                        message=str(msg),
                    )
                ],
            )
        return fuel

    def is_fuel_consumer(self) -> bool:
        return self.consumes == ConsumptionType.FUEL

    def is_electricity_consumer(self) -> bool:
        return self.consumes == ConsumptionType.ELECTRICITY

    def is_provider(self) -> bool:
        return False

    def is_container(self) -> bool:
        return True

    def get_component_process_type(self) -> ComponentType:
        return self.component_type

    def get_name(self) -> str:
        return self.name

    def evaluate_energy_usage(self, context: ComponentEnergyContext) -> dict[str, EcalcModelResult]:
        consumer_results = {}
        evaluated_stream_conditions = self.evaluate_stream_conditions()
        optimizer = PriorityOptimizer()

        results_per_period: dict[str, dict[Period, ComponentResult]] = defaultdict(dict)
        priorities_used = []
        for period in self.expression_evaluator.get_periods():
            consumers_for_period = [
                create_consumer(
                    consumer=consumer,
                    period=period,
                )
                for consumer in self.consumers
            ]

            consumer_system = ConsumerSystemEnergyComponent(
                id=self.id,
                consumers=consumers_for_period,
                component_conditions=self.component_conditions,
            )

            def evaluator(priority: PriorityID):
                stream_conditions_for_priority = evaluated_stream_conditions[priority]
                stream_conditions_for_timestep = {
                    component_id: [stream_condition.for_period(period) for stream_condition in stream_conditions]
                    for component_id, stream_conditions in stream_conditions_for_priority.items()
                }
                return consumer_system.evaluate_consumers(stream_conditions_for_timestep)

            optimizer_result = optimizer.optimize(
                priorities=list(evaluated_stream_conditions.keys()),
                evaluator=evaluator,
            )
            priorities_used.append(optimizer_result.priority_used)
            for consumer_result in optimizer_result.priority_results:
                results_per_period[consumer_result.id][period] = consumer_result

        priorities_used = TimeSeriesString(
            periods=self.expression_evaluator.get_periods(),
            values=priorities_used,
            unit=Unit.NONE,
        )
        # merge consumer results
        consumer_ids = [consumer.id for consumer in self.consumers]
        merged_consumer_results = []
        for consumer_id in consumer_ids:
            first_result, *rest_results = list(results_per_period[consumer_id].values())
            merged_consumer_results.append(first_result.merge(*rest_results))

        # Convert to legacy compatible operational_settings_used
        priorities_to_int_map = {
            priority_name: index + 1 for index, priority_name in enumerate(evaluated_stream_conditions.keys())
        }
        operational_settings_used = TimeSeriesInt(
            periods=priorities_used.periods,
            values=[priorities_to_int_map[priority_name] for priority_name in priorities_used.values],
            unit=priorities_used.unit,
        )

        system_result = ConsumerSystemEnergyComponent.get_system_result(
            id=self.id,
            consumer_results=merged_consumer_results,
            operational_settings_used=operational_settings_used,
        )
        consumer_results[self.id] = system_result
        for consumer_result in merged_consumer_results:
            consumer_results[consumer_result.id] = EcalcModelResult(
                component_result=consumer_result,
                sub_components=[],
                models=[],
            )

        self.consumer_results = consumer_results
        return self.consumer_results

    def evaluate_emissions(
        self,
        energy_context: ComponentEnergyContext,
        energy_model: EnergyModel,
    ) -> Optional[dict[str, EmissionResult]]:
        if self.is_fuel_consumer():
            assert self.fuel is not None
            fuel_model = FuelModel(self.fuel)
            fuel_usage = energy_context.get_fuel_usage()

            assert fuel_usage is not None

            self.emission_results = fuel_model.evaluate_emissions(
                fuel_rate=fuel_usage.values,
                expression_evaluator=self.expression_evaluator,
            )
        return self.emission_results

    def get_graph(self) -> ComponentGraph:
        graph = ComponentGraph()
        graph.add_node(self)
        for consumer in self.consumers:
            graph.add_node(consumer)
            graph.add_edge(self.id, consumer.id)
        return graph

    def evaluate_stream_conditions(self) -> Priorities[dict[ConsumerID, list[TimeSeriesStreamConditions]]]:
        parsed_priorities: Priorities[dict[ConsumerID, list[TimeSeriesStreamConditions]]] = defaultdict(dict)
        for priority_name, priority in self.stream_conditions_priorities.items():
            for consumer_name, streams_conditions in priority.items():
                parsed_priorities[priority_name][generate_id(consumer_name)] = [
                    TimeSeriesStreamConditions(
                        id=generate_id(consumer_name, stream_name),
                        name="-".join([consumer_name, stream_name]),
                        rate=TimeSeriesStreamDayRate(
                            periods=self.expression_evaluator.get_periods(),
                            values=list(
                                self.expression_evaluator.evaluate(
                                    Expression.setup_from_expression(stream_conditions["rate"].value)
                                )
                            ),
                            unit=stream_conditions["rate"].unit,
                        )
                        if stream_conditions and "rate" in stream_conditions and stream_conditions["rate"] is not None
                        else None,
                        pressure=TimeSeriesFloat(
                            periods=self.expression_evaluator.get_periods(),
                            values=list(
                                self.expression_evaluator.evaluate(
                                    expression=Expression.setup_from_expression(stream_conditions["pressure"].value)
                                )
                            ),
                            unit=stream_conditions["pressure"].unit,
                        )
                        if stream_conditions
                        and "pressure" in stream_conditions
                        and stream_conditions["pressure"] is not None
                        else None,
                        fluid_density=TimeSeriesFloat(
                            periods=self.expression_evaluator.get_periods(),
                            values=list(
                                self.expression_evaluator.evaluate(
                                    expression=Expression.setup_from_expression(
                                        stream_conditions["fluid_density"].value
                                    )
                                )
                            ),
                            unit=stream_conditions["fluid_density"].unit,
                        )
                        if stream_conditions
                        and "fluid_density" in stream_conditions
                        and stream_conditions["fluid_density"] is not None
                        else None,
                    )
                    for stream_name, stream_conditions in streams_conditions.items()
                ]
        return dict(parsed_priorities)


def create_consumer(
    consumer: Union[CompressorComponent, PumpComponent],
    period: Period,
) -> Union[Compressor, Pump]:
    periods = consumer.energy_usage_model.keys()
    energy_usage_models = list(consumer.energy_usage_model.values())

    model_for_period = None
    for _period, energy_usage_model in zip(periods, energy_usage_models):
        if period in _period:
            model_for_period = energy_usage_model

    if model_for_period is None:
        raise ComponentValidationException(
            errors=[
                ModelValidationError(
                    name=consumer.name,
                    message=f"Could not find model at timestep {period}",
                )
            ]
        )

    if consumer.component_type in {ComponentType.COMPRESSOR, ComponentType.COMPRESSOR_V2}:
        return Compressor(
            id=consumer.id,
            compressor_model=create_compressor_model(
                compressor_model_dto=model_for_period,
            ),
        )
    elif consumer.component_type in {ComponentType.PUMP, ComponentType.PUMP_V2}:
        return Pump(
            id=consumer.id,
            pump_model=create_pump_model(
                pump_model_dto=model_for_period,
            ),
        )
    else:
        raise TypeError(f"Unknown consumer. Received consumer with type '{consumer.component_type}'")
