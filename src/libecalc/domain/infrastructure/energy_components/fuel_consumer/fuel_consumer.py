from libecalc.common.component_type import ComponentType
from libecalc.common.consumption_type import ConsumptionType
from libecalc.common.temporal_model import TemporalModel
from libecalc.common.time_utils import Period
from libecalc.common.variables import ExpressionEvaluator
from libecalc.core.result import EcalcModelResult
from libecalc.core.result.emission import EmissionResult
from libecalc.domain.energy import ComponentEnergyContext, Emitter, EnergyComponent, EnergyModel
from libecalc.domain.infrastructure.energy_components.fuel_model.fuel_model import FuelModel
from libecalc.domain.infrastructure.energy_components.legacy_consumer.component import (
    Consumer as ConsumerEnergyComponent,
)
from libecalc.domain.infrastructure.energy_components.legacy_consumer.consumer_function import ConsumerFunction
from libecalc.domain.infrastructure.path_id import PathID
from libecalc.domain.process.process_change_event import ProcessChangedEvent
from libecalc.domain.process.process_system import ProcessSystem
from libecalc.domain.process.temporal_process_system import TemporalProcessSystem
from libecalc.domain.regularity import Regularity
from libecalc.dto.fuel_type import FuelType
from libecalc.dto.types import ConsumerUserDefinedCategoryType


class FuelConsumer(Emitter, TemporalProcessSystem, EnergyComponent):
    def get_process_changed_events(self) -> list[ProcessChangedEvent]:
        return [
            ProcessChangedEvent(
                start=period.start,
                name=str(period.start),
            )
            for period in self.energy_usage_model.get_periods()
        ]

    def get_process_system(self, event: ProcessChangedEvent) -> ProcessSystem | None:
        # TODO: implement ProcessSystem for all EnergyUsageModels, rename them to ProcessSystem?
        raise NotImplementedError()

    def __init__(
        self,
        path_id: PathID,
        regularity: Regularity,
        user_defined_category: dict[Period, ConsumerUserDefinedCategoryType],
        component_type: ComponentType,
        fuel: TemporalModel[FuelType],
        energy_usage_model: TemporalModel[ConsumerFunction],
        expression_evaluator: ExpressionEvaluator,
    ):
        assert fuel is not None
        self._path_id = path_id
        self.regularity = regularity
        self.user_defined_category = user_defined_category
        self.energy_usage_model: TemporalModel[ConsumerFunction] = energy_usage_model
        self.expression_evaluator = expression_evaluator
        self.fuel: TemporalModel[FuelType] = fuel
        self.component_type = component_type
        self.consumer_results: dict[str, EcalcModelResult] = {}
        self.emission_results: dict[str, EmissionResult] | None = None

    @property
    def name(self):
        return self._path_id.get_name()

    @property
    def id(self) -> str:
        return self._path_id.get_name()

    def is_fuel_consumer(self) -> bool:
        return True

    def is_electricity_consumer(self) -> bool:
        return False

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
            consumes=ConsumptionType.FUEL,
            energy_usage_model=self.energy_usage_model,
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
