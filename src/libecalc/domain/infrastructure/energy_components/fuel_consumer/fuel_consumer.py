import logging
from uuid import UUID

from libecalc.common.component_type import ComponentType
from libecalc.common.consumption_type import ConsumptionType
from libecalc.common.temporal_model import TemporalModel
from libecalc.common.utils.rates import TimeSeriesRate
from libecalc.common.variables import ExpressionEvaluator
from libecalc.core.result import EcalcModelResult
from libecalc.core.result.emission import EmissionResult
from libecalc.domain.energy import ComponentEnergyContext, Emitter, EnergyComponent, EnergyModel
from libecalc.domain.energy.emitter import EmissionName
from libecalc.domain.fuel import Fuel
from libecalc.domain.infrastructure.energy_components.fuel_model.fuel_model import FuelModel
from libecalc.domain.infrastructure.energy_components.legacy_consumer.component import (
    Consumer as ConsumerEnergyComponent,
)
from libecalc.domain.infrastructure.energy_components.legacy_consumer.consumer_function import ConsumerFunction
from libecalc.domain.infrastructure.path_id import PathID
from libecalc.domain.installation import FuelConsumer, FuelConsumption
from libecalc.domain.process.process_change_event import ProcessChangedEvent
from libecalc.domain.process.process_system import ProcessSystem
from libecalc.domain.process.temporal_process_system import TemporalProcessSystem
from libecalc.domain.regularity import Regularity
from libecalc.dto.fuel_type import FuelType

logger = logging.getLogger(__name__)


class FuelConsumerComponent(Emitter, TemporalProcessSystem, EnergyComponent, FuelConsumer):
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
        path_id: PathID,
        regularity: Regularity,
        component_type: ComponentType,
        fuel: TemporalModel[FuelType],
        energy_usage_model: TemporalModel[ConsumerFunction],
        expression_evaluator: ExpressionEvaluator,
    ):
        self._uuid = id
        assert fuel is not None
        self._path_id = path_id
        self.regularity = regularity
        self.energy_usage_model: TemporalModel[ConsumerFunction] = energy_usage_model
        self.expression_evaluator = expression_evaluator
        self.fuel: TemporalModel[FuelType] = fuel
        self.component_type = component_type
        self.consumer_results: dict[str, EcalcModelResult] = {}
        self.emission_results: dict[str, EmissionResult] | None = None

    def get_id(self) -> UUID:
        return self._uuid

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

    def get_fuel_consumption(self) -> FuelConsumption:
        fuel_rate = self.consumer_results[self.id].component_result.energy_usage
        return FuelConsumption(
            rate=TimeSeriesRate.from_timeseries_stream_day_rate(fuel_rate, regularity=self.regularity.time_series),
            fuel=self.fuel,  # type: ignore[arg-type]
        )

    def get_power_consumption(self) -> TimeSeriesRate | None:
        power = self.consumer_results[self.id].component_result.power
        if power is None:
            return None

        if 0 < len(power) == len(self.expression_evaluator.get_periods()) and len(
            self.consumer_results[self.id].component_result.periods
        ) == len(power.periods):
            return TimeSeriesRate.from_timeseries_stream_day_rate(power, regularity=self.regularity.time_series)
        else:
            logger.warning(
                f"A combination of one or more compressors that do not support fuel to power conversion was used."
                f"We are therefore unable to calculate correct power usage. Please only use compressors which support POWER conversion"
                f"for fuel consumer '{self.get_name()}'"
            )

    def get_fuel(self) -> TemporalModel[Fuel]:
        return self.fuel

    def get_emissions(self) -> dict[EmissionName, TimeSeriesRate]:
        emissions = self.emission_results
        assert emissions is not None
        return {
            emission_name: TimeSeriesRate.from_timeseries_stream_day_rate(emission.rate, self.regularity.time_series)
            for emission_name, emission in emissions.items()
        }
