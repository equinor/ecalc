import numpy as np

from libecalc.common.component_type import ComponentType
from libecalc.common.string.string_utils import generate_id
from libecalc.common.temporal_model import TemporalModel
from libecalc.common.time_utils import Period
from libecalc.common.units import Unit
from libecalc.common.utils.rates import Rates, RateType, TimeSeriesFloat, TimeSeriesStreamDayRate
from libecalc.common.variables import ExpressionEvaluator
from libecalc.core.result.emission import EmissionResult
from libecalc.domain.energy import ComponentEnergyContext, Emitter, EnergyComponent, EnergyModel
from libecalc.dto.types import ConsumerUserDefinedCategoryType
from libecalc.dto.utils.validators import convert_expression
from libecalc.expression import Expression
from libecalc.expression.expression import ExpressionType


class VentingType:
    DIRECT_EMISSION = "DIRECT_EMISSION"
    OIL_VOLUME = "OIL_VOLUME"


# Direct emitter classes
class EmissionRate:
    def __init__(self, value: ExpressionType, unit: Unit, rate_type: RateType):
        self.value = value
        self.unit = unit
        self.rate_type = rate_type


class VentingEmission:
    def __init__(self, name: str, emission_rate: EmissionRate):
        self.name = name
        self.emission_rate = emission_rate


# Oil type emitter classes
class OilVolumeRate:
    def __init__(self, value: ExpressionType, unit: Unit, rate_type: RateType):
        self.value = value
        self.unit = unit
        self.rate_type = rate_type


class VentingVolumeEmission:
    def __init__(self, name: str, emission_factor: ExpressionType):
        self.name = name
        self.emission_factor = emission_factor


class VentingVolume:
    def __init__(self, oil_volume_rate: OilVolumeRate, emissions: list[VentingVolumeEmission]):
        self.oil_volume_rate = oil_volume_rate
        self.emissions = emissions


class VentingEmitter(Emitter, EnergyComponent):
    def __init__(
        self,
        name: str,
        expression_evaluator: ExpressionEvaluator,
        component_type: ComponentType,
        user_defined_category: dict[Period, ConsumerUserDefinedCategoryType],
        emitter_type: VentingType,
        regularity: dict[Period, Expression],
    ):
        self.name = name
        self.expression_evaluator = expression_evaluator
        self.component_type = component_type
        self.user_defined_category = user_defined_category
        self.emitter_type = emitter_type
        self._regularity = regularity
        self.emission_results: dict[str, EmissionResult] | None = None

    @property
    def id(self) -> str:
        return generate_id(self.name)

    @property
    def regularity_evaluated(self):
        return self.expression_evaluator.evaluate(expression=TemporalModel(self._regularity)).tolist()

    def evaluate_emissions(
        self,
        energy_context: ComponentEnergyContext | None = None,
        energy_model: EnergyModel | None = None,
    ) -> dict[str, EmissionResult] | None:
        venting_emitter_results = {}
        emission_rates = self.get_emissions()

        for emission_name, emission_rate in emission_rates.items():
            emission_result = EmissionResult(
                name=emission_name,
                periods=self.expression_evaluator.get_periods(),
                rate=emission_rate,
            )
            venting_emitter_results[emission_name] = emission_result
        self.emission_results = venting_emitter_results
        return self.emission_results

    def get_emissions(self) -> dict[str, TimeSeriesStreamDayRate]:
        raise NotImplementedError("Subclasses should implement this method")

    def _evaluate_emission_rate(self, emission):
        emission_rate = self.expression_evaluator.evaluate(
            Expression.setup_from_expression(value=emission.emission_rate.value)
        )
        if emission.emission_rate.rate_type == RateType.CALENDAR_DAY:
            emission_rate = Rates.to_stream_day(
                calendar_day_rates=np.asarray(emission_rate), regularity=self.regularity_evaluated
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

    def is_container(self) -> bool:
        return False


class DirectVentingEmitter(VentingEmitter):
    def __init__(self, emissions: list[VentingEmission], **kwargs):
        super().__init__(**kwargs)
        self.emissions = emissions
        self.emitter_type = VentingType.DIRECT_EMISSION

    def get_emissions(self) -> dict[str, TimeSeriesStreamDayRate]:
        emissions = {}
        for emission in self.emissions:
            emission_rate = self._evaluate_emission_rate(emission)
            emissions[emission.name] = self._create_time_series(emission_rate)
        return emissions


class OilVentingEmitter(VentingEmitter):
    def __init__(self, volume: VentingVolume, **kwargs):
        super().__init__(**kwargs)
        self.volume = volume
        self.emitter_type = VentingType.OIL_VOLUME

    def get_emissions(self) -> dict[str, TimeSeriesStreamDayRate]:
        oil_rates = self.get_oil_rates(self.regularity_evaluated)
        emissions = {}
        for emission in self.volume.emissions:
            factors = self.expression_evaluator.evaluate(
                Expression.setup_from_expression(value=emission.emission_factor)
            )

            emission_rate = [oil_rate * factor for oil_rate, factor in zip(oil_rates.values, factors)]
            emission_rate = Unit.KILO_PER_DAY.to(Unit.TONS_PER_DAY)(emission_rate)
            emissions[emission.name] = self._create_time_series(emission_rate)
        return emissions

    def get_oil_rates(self, regularity: [TimeSeriesFloat, list[float]]) -> TimeSeriesStreamDayRate:
        if isinstance(regularity, TimeSeriesFloat):
            regularity = regularity.values

        oil_rates = self.expression_evaluator.evaluate(expression=convert_expression(self.volume.oil_volume_rate.value))

        if self.volume.oil_volume_rate.rate_type == RateType.CALENDAR_DAY:
            oil_rates = Rates.to_stream_day(
                calendar_day_rates=np.asarray(oil_rates),
                regularity=regularity,
            ).tolist()

        unit = self.volume.oil_volume_rate.unit
        oil_rates = unit.to(Unit.STANDARD_CUBIC_METER_PER_DAY)(oil_rates)

        return TimeSeriesStreamDayRate(
            periods=self.expression_evaluator.get_periods(),
            values=oil_rates,
            unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
        )
