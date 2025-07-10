import abc
from typing import cast
from uuid import UUID

import numpy as np

from libecalc.common.component_type import ComponentType
from libecalc.common.list.list_utils import array_to_list
from libecalc.common.units import Unit
from libecalc.common.utils.rates import Rates, RateType, TimeSeriesRate, TimeSeriesStreamDayRate
from libecalc.common.variables import ExpressionEvaluator
from libecalc.core.result.emission import EmissionResult
from libecalc.domain.energy import ComponentEnergyContext, Emitter, EnergyComponent, EnergyModel
from libecalc.domain.energy.emitter import EmissionName
from libecalc.domain.infrastructure.energy_components.legacy_consumer.consumer_function.utils import (
    apply_condition,
    get_condition_from_expression,
)
from libecalc.domain.infrastructure.path_id import PathID
from libecalc.domain.installation import StorageContainer
from libecalc.domain.regularity import Regularity
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


class VentingVolume:
    def __init__(self, oil_volume_rate: OilVolumeRate, emissions: list[VentingVolumeEmission]):
        self.oil_volume_rate = oil_volume_rate
        self.emissions = emissions


class VentingEmitter(Emitter, EnergyComponent, abc.ABC):
    def __init__(
        self,
        id: UUID,
        path_id: PathID,
        expression_evaluator: ExpressionEvaluator,
        component_type: ComponentType,
        emitter_type: VentingType,
        regularity: Regularity,
    ):
        self._uuid = id
        self._path_id = path_id
        self.expression_evaluator = expression_evaluator
        self.component_type = component_type
        self.emitter_type = emitter_type
        self.regularity = regularity
        self.emission_results: dict[str, EmissionResult] | None = None

    def get_id(self) -> UUID:
        return self._uuid

    @property
    def name(self) -> str:
        return self._path_id.get_name()

    @property
    def id(self) -> str:
        return self._path_id.get_name()

    def evaluate_emissions(
        self,
        energy_context: ComponentEnergyContext | None = None,
        energy_model: EnergyModel | None = None,
    ) -> dict[str, EmissionResult] | None:
        venting_emitter_results = {}
        emission_rates = self._get_emissions()

        for emission_name, emission_rate in emission_rates.items():
            emission_result = EmissionResult(
                name=emission_name,
                periods=self.expression_evaluator.get_periods(),
                rate=emission_rate,
            )
            venting_emitter_results[emission_name] = emission_result
        self.emission_results = venting_emitter_results
        return self.emission_results

    @abc.abstractmethod
    def _get_emissions(self) -> dict[str, TimeSeriesStreamDayRate]: ...

    def get_emissions(self) -> dict[EmissionName, TimeSeriesRate]:
        return {
            emission_name: TimeSeriesRate.from_timeseries_stream_day_rate(emission_rate, self.regularity.time_series)
            for emission_name, emission_rate in self._get_emissions().items()
        }

    def _evaluate_emission_rate(self, emission):
        emission_rate = self.expression_evaluator.evaluate(
            Expression.setup_from_expression(value=emission.emission_rate.value)
        )
        if emission.emission_rate.rate_type == RateType.CALENDAR_DAY:
            emission_rate = Rates.to_stream_day(
                calendar_day_rates=np.asarray(emission_rate), regularity=self.regularity.time_series.values
            ).tolist()
        unit = emission.emission_rate.unit
        emission_rate = unit.to(Unit.TONS_PER_DAY)(emission_rate)
        return emission_rate

    def _create_time_series(self, emission_rate):
        return TimeSeriesStreamDayRate(
            periods=self.expression_evaluator.get_periods(),
            values=emission_rate,
            unit=Unit.TONS_PER_DAY,
        )

    def is_fuel_consumer(self) -> bool:
        return False

    def is_electricity_consumer(self) -> bool:
        return False

    def get_component_process_type(self) -> ComponentType:
        return self.component_type

    def get_name(self) -> str:
        return self.name

    def is_provider(self) -> bool:
        return False


class DirectVentingEmitter(VentingEmitter):
    def __init__(self, emissions: list[VentingEmission], **kwargs):
        super().__init__(**kwargs)
        self.emissions = emissions
        self.emitter_type = VentingType.DIRECT_EMISSION

    def _get_emissions(self) -> dict[str, TimeSeriesStreamDayRate]:
        emissions = {}
        for emission in self.emissions:
            condition = get_condition_from_expression(
                expression_evaluator=self.expression_evaluator,
                condition_expression=emission.emission_rate.condition,
            )
            emission_rate = self._evaluate_emission_rate(emission)
            emission_rate = apply_condition(input_array=emission_rate, condition=condition)
            emissions[emission.name] = self._create_time_series(emission_rate)
        return emissions


class OilVentingEmitter(VentingEmitter, StorageContainer):
    def __init__(self, volume: VentingVolume, **kwargs):
        super().__init__(**kwargs)
        self.volume = volume
        self.emitter_type = VentingType.OIL_VOLUME

    def _get_emissions(self) -> dict[str, TimeSeriesStreamDayRate]:
        oil_rates = self.get_oil_rates()
        emissions = {}
        for emission in self.volume.emissions:
            factors = self.expression_evaluator.evaluate(
                Expression.setup_from_expression(value=emission.emission_factor)
            )

            emission_rate = [oil_rate * factor for oil_rate, factor in zip(oil_rates.values, factors)]
            emission_rate = Unit.KILO_PER_DAY.to(Unit.TONS_PER_DAY)(emission_rate)
            emissions[emission.name] = self._create_time_series(emission_rate)
        return emissions

    def get_oil_rates(self) -> TimeSeriesRate:
        oil_rates = self.expression_evaluator.evaluate(expression=convert_expression(self.volume.oil_volume_rate.value))  # type: ignore[arg-type]
        oil_rates = (
            TimeSeriesRate(
                values=array_to_list(oil_rates),
                periods=self.expression_evaluator.get_periods(),
                unit=self.volume.oil_volume_rate.unit,
                regularity=self.regularity.time_series.values,
                rate_type=self.volume.oil_volume_rate.rate_type,
            )
            .to_stream_day()
            .to_unit(Unit.STANDARD_CUBIC_METER_PER_DAY)
        )

        condition = get_condition_from_expression(
            expression_evaluator=self.expression_evaluator,
            condition_expression=self.volume.oil_volume_rate.condition,
        )
        oil_rates.values = array_to_list(apply_condition(oil_rates.values, condition=condition))

        return cast(TimeSeriesRate, oil_rates)

    def get_storage_rates(self) -> TimeSeriesRate:
        return self.get_oil_rates()
