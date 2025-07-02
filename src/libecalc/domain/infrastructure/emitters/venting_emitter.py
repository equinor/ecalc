from typing import cast

from libecalc.common.component_type import ComponentType
from libecalc.common.units import Unit
from libecalc.common.utils.rates import (
    RateType,
    TimeSeriesRate,
    TimeSeriesStreamDayRate,
    TimeSeriesVolumes,
)
from libecalc.common.variables import ExpressionEvaluator
from libecalc.core.result.emission import EmissionResult
from libecalc.domain.energy import ComponentEnergyContext, Emitter, EnergyComponent, EnergyModel
from libecalc.domain.infrastructure.energy_components.legacy_consumer.consumer_function.utils import (
    apply_condition,
    get_condition_from_expression,
)
from libecalc.domain.infrastructure.path_id import PathID
from libecalc.domain.regularity import Regularity
from libecalc.domain.storage_container import StorageContainer
from libecalc.dto.types import ConsumerUserDefinedCategoryType
from libecalc.dto.utils.validators import convert_expression
from libecalc.expression import Expression
from libecalc.expression.expression import ExpressionType


class VentingType:
    DIRECT_EMISSION = "DIRECT_EMISSION"
    OIL_VOLUME = "OIL_VOLUME"


# Direct emitter classes
class EmissionRate:
    def __init__(self, value: ExpressionType, unit: Unit, rate_type: RateType, condition: Expression | None = None):
        self.value = value
        self.unit = unit
        self.rate_type = rate_type
        self.condition = condition


class VentingEmission:
    def __init__(self, name: str, emission_rate: EmissionRate):
        self.name = name
        self.emission_rate = emission_rate


# Oil type emitter classes
class OilVolumeRate:
    def __init__(
        self,
        value: ExpressionType,
        unit: Unit,
        rate_type: RateType,
        condition: Expression | None = None,
    ):
        self.value = value
        self.unit = unit
        self.rate_type = rate_type
        self.condition = condition


class VentingVolumeEmission:
    def __init__(self, name: str, emission_factor: ExpressionType):
        self.name = name
        self.emission_factor = emission_factor


class VentingEmitterComponent(EnergyComponent):
    def __init__(
        self,
        path_id: PathID,
        user_defined_category: ConsumerUserDefinedCategoryType,
        emitter_type: VentingType,
    ):
        super().__init__(entity_id=path_id)
        self.user_defined_category = user_defined_category
        self.emitter_type = emitter_type

    @property
    def id(self):
        return self.get_id().get_name()

    def is_fuel_consumer(self) -> bool:
        return False

    def is_electricity_consumer(self) -> bool:
        return False

    def get_component_process_type(self) -> ComponentType:
        return ComponentType.VENTING_EMITTER

    def get_name(self) -> str:
        return self.get_id().get_name()

    def is_provider(self) -> bool:
        return False


class DirectVentingEmitter(Emitter):
    def __init__(
        self,
        emissions: list[VentingEmission],
        path_id: PathID,
        expression_evaluator: ExpressionEvaluator,
        regularity: Regularity,
    ):
        super().__init__(entity_id=path_id)
        self.emissions = emissions
        self.emitter_type = VentingType.DIRECT_EMISSION
        self.expression_evaluator = expression_evaluator
        self.regularity = regularity
        self.emission_results: dict[str, EmissionResult] | None = None

    @property
    def id(self):
        return self.get_id().get_name()

    def evaluate_emissions(
        self,
        energy_context: ComponentEnergyContext | None = None,
        energy_model: EnergyModel | None = None,
    ) -> dict[str, TimeSeriesStreamDayRate] | None:
        emissions = {}
        for emission in self.emissions:
            condition = get_condition_from_expression(
                expression_evaluator=self.expression_evaluator,
                condition_expression=emission.emission_rate.condition,
            )
            emission_rate = (
                TimeSeriesRate(
                    values=self.expression_evaluator.evaluate(
                        Expression.setup_from_expression(emission.emission_rate.value)
                    ).tolist(),
                    periods=self.expression_evaluator.get_periods(),
                    unit=emission.emission_rate.unit,
                    rate_type=emission.emission_rate.rate_type,
                    regularity=self.regularity.get_values(),
                )
                .to_stream_day()
                .to_unit(Unit.TONS_PER_DAY)
            )
            emission_rate = cast(TimeSeriesRate, emission_rate)
            emission_rate.values = apply_condition(emission_rate.values, condition).tolist()
            emissions[emission.name] = emission_rate.to_stream_day_timeseries()
        return emissions


class OilStorageContainer(StorageContainer):
    def __init__(
        self,
        oil_volume_rate: OilVolumeRate,
        path_id: PathID,
        expression_evaluator: ExpressionEvaluator,
        regularity: Regularity,
    ):
        super().__init__(entity_id=path_id)
        self._oil_volume_rate = oil_volume_rate
        self.expression_evaluator = expression_evaluator
        self.regularity = regularity

    def get_oil_rates(self) -> TimeSeriesRate:
        oil_rates = self.expression_evaluator.evaluate(expression=convert_expression(self._oil_volume_rate.value))  # type: ignore[arg-type]

        oil_rates = (
            TimeSeriesRate(
                values=oil_rates.tolist(),
                periods=self.expression_evaluator.get_periods(),
                unit=self._oil_volume_rate.unit,
                regularity=self.regularity.get_values(),
                rate_type=self._oil_volume_rate.rate_type,
            )
            .to_stream_day()
            .to_unit(Unit.STANDARD_CUBIC_METER_PER_DAY)
        )

        condition = get_condition_from_expression(
            expression_evaluator=self.expression_evaluator,
            condition_expression=self._oil_volume_rate.condition,
        )

        oil_rates.values = apply_condition(oil_rates.values, condition).tolist()

        return cast(TimeSeriesRate, oil_rates)

    def get_storage_rates(self) -> TimeSeriesStreamDayRate:
        return self.get_oil_rates().to_stream_day_timeseries()

    def get_storage_volumes(self) -> TimeSeriesVolumes:
        return self.get_oil_rates().to_volumes()


class OilVentingEmitter(Emitter):
    def __init__(
        self,
        emissions: list[VentingVolumeEmission],
        path_id: PathID,
        expression_evaluator: ExpressionEvaluator,
        regularity: Regularity,
    ):
        super().__init__(entity_id=path_id)
        self._emissions = emissions
        self.expression_evaluator = expression_evaluator
        self.regularity = regularity
        self.emission_results: dict[str, EmissionResult] | None = None

    @property
    def id(self):
        return self.get_id().get_name()

    def evaluate_emissions(
        self,
        energy_context: ComponentEnergyContext | None = None,
        energy_model: EnergyModel | None = None,
    ) -> dict[str, TimeSeriesStreamDayRate] | None:
        # TODO: This is very similar to FuelConsumerEmitter, consider if it should be the same emitter handling this (EmissionFactorEmitter)
        emissions = {}
        oil_rates = energy_context.get_storage_volume()
        for emission in self._emissions:
            factors = self.expression_evaluator.evaluate(
                Expression.setup_from_expression(value=emission.emission_factor)
            )

            emission_rate = [oil_rate * factor for oil_rate, factor in zip(oil_rates.values, factors)]
            emission_rate = Unit.KILO_PER_DAY.to(Unit.TONS_PER_DAY)(emission_rate)
            emissions[emission.name] = TimeSeriesStreamDayRate(
                periods=self.expression_evaluator.get_periods(),
                values=emission_rate,
                unit=Unit.TONS_PER_DAY,
            )
        return emissions
