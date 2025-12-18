from typing import Literal, Union
from uuid import UUID

from libecalc.common.component_type import ComponentType
from libecalc.common.consumption_type import ConsumptionType
from libecalc.common.temporal_model import TemporalModel
from libecalc.common.utils.rates import TimeSeriesRate
from libecalc.common.variables import ExpressionEvaluator
from libecalc.core.result import CompressorResult, ConsumerSystemResult
from libecalc.core.result.results import GenericComponentResult, PumpResult
from libecalc.domain.energy import ComponentEnergyContext, EnergyComponent
from libecalc.domain.infrastructure.energy_components.legacy_consumer.component import (
    Consumer as ConsumerEnergyComponent,
)
from libecalc.domain.infrastructure.energy_components.legacy_consumer.consumer_function import ConsumerFunction
from libecalc.domain.process.compressor.core.base import CompressorWithTurbineModel
from libecalc.domain.process.compressor.core.sampled import CompressorModelSampled
from libecalc.domain.process.compressor.core.train.base import CompressorTrainModel
from libecalc.domain.process.process_change_event import ProcessChangedEvent
from libecalc.domain.process.process_system import ProcessSystem
from libecalc.domain.process.pump.pump import PumpModel
from libecalc.domain.process.temporal_process_system import TemporalProcessSystem
from libecalc.domain.regularity import Regularity

EnergyUsageModelType = Union[
    TemporalModel[ConsumerFunction],
    TemporalModel[CompressorTrainModel | CompressorModelSampled | CompressorWithTurbineModel],
    TemporalModel[PumpModel],
]


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
        # TODO: implement ProcessSystem for all EnergyUsageModels, rename them to ProcessSystem?
        raise NotImplementedError()

    def __init__(
        self,
        id: UUID,
        name: str,
        regularity: Regularity,
        component_type: ComponentType,
        energy_usage_model: EnergyUsageModelType,
        expression_evaluator: ExpressionEvaluator,
        consumes: Literal[ConsumptionType.ELECTRICITY] = ConsumptionType.ELECTRICITY,
    ):
        self._uuid = id
        self._name = name
        self.regularity = regularity
        self.energy_usage_model = energy_usage_model
        self.expression_evaluator = expression_evaluator
        self.consumes = consumes
        self.component_type = component_type
        self._consumer_result: ConsumerSystemResult | CompressorResult | PumpResult | GenericComponentResult | None = (
            None
        )

    def get_id(self) -> UUID:
        return self._uuid

    @property
    def name(self):
        return self._name

    def is_fuel_consumer(self) -> bool:
        return False

    def is_electricity_consumer(self) -> bool:
        return True

    def is_provider(self) -> bool:
        return False

    def get_component_process_type(self) -> ComponentType:
        return self.component_type

    def get_name(self) -> str:
        return self.name

    def evaluate_energy_usage(self, context: ComponentEnergyContext) -> ConsumerSystemResult | GenericComponentResult:
        consumer = ConsumerEnergyComponent(
            id=self.name,
            name=self.name,
            component_type=self.component_type,
            regularity=self.regularity,
            consumes=self.consumes,
            energy_usage_model=self.energy_usage_model,
        )
        res = consumer.evaluate(expression_evaluator=self.expression_evaluator)
        self._consumer_result = res
        return res

    def get_power_consumption(self) -> TimeSeriesRate | None:
        power = self._consumer_result.power
        if power is None:
            return None
        return TimeSeriesRate.from_timeseries_stream_day_rate(power, regularity=self.regularity.time_series)
