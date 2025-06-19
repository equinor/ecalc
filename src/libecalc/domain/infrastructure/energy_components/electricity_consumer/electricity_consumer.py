from typing import Literal

from libecalc.common.component_type import ComponentType
from libecalc.common.consumption_type import ConsumptionType
from libecalc.common.temporal_model import TemporalModel
from libecalc.common.time_utils import Period
from libecalc.common.variables import ExpressionEvaluator
from libecalc.core.result import EcalcModelResult
from libecalc.domain.energy import ComponentEnergyContext, EnergyComponent
from libecalc.domain.infrastructure.energy_components.legacy_consumer.component import (
    Consumer as ConsumerEnergyComponent,
)
from libecalc.domain.infrastructure.energy_components.legacy_consumer.consumer_function import ConsumerFunction
from libecalc.domain.infrastructure.path_id import PathID
from libecalc.domain.process.process_change_event import ProcessChangedEvent
from libecalc.domain.process.process_system import ProcessEntityID, ProcessSystem, ProcessUnit
from libecalc.domain.process.temporal_process_system import TemporalProcessSystem
from libecalc.domain.regularity import Regularity
from libecalc.dto.types import ConsumerUserDefinedCategoryType


class ElectricityConsumerProcessSystem(ProcessSystem):
    def __init__(self, consumer_id: ProcessEntityID, name: str, model_results: list, event: ProcessChangedEvent):
        self._id = consumer_id
        self._name = name
        self._model_results = model_results
        self._event = event

    def get_process_units(self) -> list[ProcessSystem | ProcessUnit]:
        return self._model_results

    def get_id(self):
        return self._id

    def get_type(self):
        return "ElectricityConsumerProcessSystem"

    def get_name(self):
        return self._name


class ElectricityConsumer(EnergyComponent, TemporalProcessSystem):
    def get_process_changed_events(self) -> list[ProcessChangedEvent]:
        return [
            ProcessChangedEvent(
                start=period.start,
                name=str(period.start),
            )
            for period in self.energy_usage_model.get_periods()
        ]

    def get_process_system(self, event: ProcessChangedEvent) -> ProcessSystem | None:
        for evt, system in self.process_results.items():
            if evt.start == event.start:
                return system

    def __init__(
        self,
        path_id: PathID,
        regularity: Regularity,
        user_defined_category: dict[Period, ConsumerUserDefinedCategoryType],
        component_type: ComponentType,
        energy_usage_model: TemporalModel[ConsumerFunction],
        expression_evaluator: ExpressionEvaluator,
        consumes: Literal[ConsumptionType.ELECTRICITY] = ConsumptionType.ELECTRICITY,
    ):
        self._path_id = path_id
        self.regularity = regularity
        self.user_defined_category = user_defined_category
        self.energy_usage_model: TemporalModel[ConsumerFunction] = energy_usage_model
        self.expression_evaluator = expression_evaluator
        self.consumes = consumes
        self.component_type = component_type
        self.consumer_results: dict[str, EcalcModelResult] = {}
        self.process_results: dict[ProcessChangedEvent, ElectricityConsumerProcessSystem] = {}

    @property
    def id(self) -> str:
        return self._path_id.get_name()

    @property
    def name(self) -> str:
        return self._path_id.get_name()

    def is_fuel_consumer(self) -> bool:
        return False

    def is_electricity_consumer(self) -> bool:
        return True

    def is_provider(self) -> bool:
        return False

    def get_component_process_type(self) -> ComponentType:
        return self.component_type

    def get_name(self) -> str:
        return self._path_id.get_name()

    def evaluate_energy_usage(self, context: ComponentEnergyContext) -> dict[str, EcalcModelResult]:
        consumer = ConsumerEnergyComponent(
            id=self.id,
            name=self.name,
            component_type=self.component_type,
            regularity=self.regularity,
            consumes=self.consumes,
            energy_usage_model=self.energy_usage_model,
        )
        self.consumer_results[self.id] = consumer.evaluate(expression_evaluator=self.expression_evaluator)

        return self.consumer_results

    def evaluate_process_results(
        self, event: ProcessChangedEvent, context: ComponentEnergyContext
    ) -> dict[ProcessChangedEvent, ElectricityConsumerProcessSystem]:
        # Find the period matching the event
        matching_period = next(
            (period for period in self.energy_usage_model.get_periods() if period.start == event.start), None
        )

        if matching_period is not None:
            energy_usage_model = self.energy_usage_model
            energy_usage_model_matched = TemporalModel(
                {
                    model.period: model.model
                    for model in energy_usage_model._models
                    if model.period.start >= matching_period.start and model.period.end <= matching_period.end
                }
            )
        else:
            energy_usage_model = {}
            energy_usage_model_matched = {}

        consumer = ConsumerEnergyComponent(
            id=self.id,
            name=self.name,
            component_type=self.component_type,
            regularity=self.regularity,
            consumes=self.consumes,
            energy_usage_model=energy_usage_model_matched,
        )
        ecalc_result = consumer.evaluate(expression_evaluator=self.expression_evaluator)
        model_results = ecalc_result.models
        self.process_results[event] = ElectricityConsumerProcessSystem(
            consumer_id=self._path_id.get_model_unique_id(),
            name=self.name,
            model_results=model_results,
            event=event,
        )

        return self.process_results
