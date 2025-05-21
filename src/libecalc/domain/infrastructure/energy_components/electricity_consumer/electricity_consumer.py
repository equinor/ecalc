from typing import Literal

from libecalc.common.component_type import ComponentType
from libecalc.common.consumption_type import ConsumptionType
from libecalc.common.energy_usage_type import EnergyUsageType
from libecalc.common.temporal_model import TemporalModel
from libecalc.common.time_utils import Period
from libecalc.common.variables import ExpressionEvaluator
from libecalc.core.result import EcalcModelResult
from libecalc.domain.energy import ComponentEnergyContext, EnergyComponent
from libecalc.domain.infrastructure.energy_components.legacy_consumer.component import (
    Consumer as ConsumerEnergyComponent,
)
from libecalc.domain.infrastructure.energy_components.legacy_consumer.consumer_function_mapper import EnergyModelMapper
from libecalc.domain.infrastructure.energy_components.utils import (
    _convert_keys_in_dictionary_from_str_to_periods,
    check_model_energy_usage_type,
)
from libecalc.domain.infrastructure.path_id import PathID
from libecalc.domain.process.dto.energy_usage_model_types import ElectricEnergyUsageModel
from libecalc.domain.process.process_change_event import ProcessChangedEvent
from libecalc.domain.process.process_system import ProcessSystem
from libecalc.domain.process.temporal_process_system import TemporalProcessSystem
from libecalc.domain.regularity import Regularity
from libecalc.dto.types import ConsumerUserDefinedCategoryType
from libecalc.dto.utils.validators import validate_temporal_model


class ElectricityConsumer(EnergyComponent, TemporalProcessSystem):
    def get_process_changed_events(self) -> list[ProcessChangedEvent]:
        return [
            ProcessChangedEvent(
                start=period.start,
                name=str(period.start),
            )
            for period in self.energy_usage_model
        ]

    def get_process_system(self, event: ProcessChangedEvent) -> ProcessSystem | None:
        # TODO: implement ProcessSystem for all EnergyUsageModels, rename them to ProcessSystem?
        raise NotImplementedError()

    def __init__(
        self,
        path_id: PathID,
        regularity: Regularity,
        user_defined_category: dict[Period, ConsumerUserDefinedCategoryType],
        component_type: Literal[
            ComponentType.COMPRESSOR,
            ComponentType.PUMP,
            ComponentType.GENERIC,
            ComponentType.PUMP_SYSTEM,
            ComponentType.COMPRESSOR_SYSTEM,
        ],
        energy_usage_model: dict[Period, ElectricEnergyUsageModel],
        expression_evaluator: ExpressionEvaluator,
        consumes: Literal[ConsumptionType.ELECTRICITY] = ConsumptionType.ELECTRICITY,
    ):
        self._path_id = path_id
        self.regularity = regularity
        self.user_defined_category = user_defined_category
        self.energy_usage_model = self.check_energy_usage_model(energy_usage_model)
        self._validate_el_consumer_temporal_model(self.energy_usage_model)
        self._check_model_energy_usage(self.energy_usage_model)
        self.expression_evaluator = expression_evaluator
        self.consumes = consumes
        self.component_type = component_type
        self.consumer_results: dict[str, EcalcModelResult] = {}

    @property
    def id(self) -> str:
        return self._path_id.get_name()

    @property
    def name(self):
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
            energy_usage_model=TemporalModel(
                {
                    period: EnergyModelMapper.from_dto_to_domain(model)
                    for period, model in self.energy_usage_model.items()
                }
            ),
        )
        self.consumer_results[self.id] = consumer.evaluate(expression_evaluator=self.expression_evaluator)

        return self.consumer_results

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
