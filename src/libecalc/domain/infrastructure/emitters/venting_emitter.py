import abc
from uuid import UUID

import numpy as np

from libecalc.common.component_type import ComponentType
from libecalc.common.time_utils import Periods
from libecalc.common.units import Unit
from libecalc.common.utils.rates import Rates, RateType, TimeSeriesRate, TimeSeriesStreamDayRate
from libecalc.domain.energy import ComponentEnergyContext, Emitter, EnergyComponent
from libecalc.domain.energy.emitter import EmissionName
from libecalc.domain.installation import StorageContainer
from libecalc.domain.regularity import Regularity
from libecalc.expression import Expression
from libecalc.expression.expression import ExpressionType
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression


class VentingType:
    DIRECT_EMISSION = "DIRECT_EMISSION"
    OIL_VOLUME = "OIL_VOLUME"


# Direct emitter classes
class EmissionRate:
    def __init__(
        self, time_series_expression: TimeSeriesExpression, unit: Unit, rate_type: RateType, regularity: Regularity
    ):
        self._time_series_expression = time_series_expression
        self.unit = unit
        self.rate_type = rate_type
        self._regularity = regularity
        self._rate_values = self._get_stream_day_values()

    def _get_stream_day_values(self) -> list[float]:
        """
        Returns the stream day emission rate values.

        The values are calculated by converting calendar day rates to stream day rates
        using the specified regularity, and then applying the given condition expression.
        """

        # if regularity is 0 for a calendar day rate, set stream day rate to 0 for that step
        rate = self._time_series_expression.get_masked_values()
        rate_array = np.asarray(rate, dtype=np.float64)

        if self.rate_type == RateType.CALENDAR_DAY:
            rate_array = Rates.to_stream_day(
                calendar_day_rates=rate_array,
                regularity=self._regularity.values,
            )

        return rate_array.tolist()

    def get_stream_day_values(self) -> list[float]:
        """
        Returns the emission rate values as a list in stream day units.

        """
        return self._rate_values

    def get_periods(self) -> Periods:
        return self._time_series_expression.expression_evaluator.get_periods()


class VentingEmission:
    def __init__(self, name: str, emission_rate: EmissionRate):
        self.name = name
        self.emission_rate = emission_rate


# Oil type emitter classes
class OilVolumeRate:
    def __init__(
        self, time_series_expression: TimeSeriesExpression, unit: Unit, rate_type: RateType, regularity: Regularity
    ):
        self._time_series_expression = time_series_expression
        self.unit = unit
        self.rate_type = rate_type
        self._regularity = regularity
        self._rate_values = self._get_stream_day_values()

    def _get_stream_day_values(self) -> list[float]:
        """
        Returns the stream day oil volume rate values.

        The values are calculated by converting calendar day rates to stream day rates
        using the specified regularity, and then applying the given condition expression.
        """

        # if regularity is 0 for a calendar day rate, set stream day rate to 0 for that step
        rate = self._time_series_expression.get_masked_values()
        rate_array = np.asarray(rate, dtype=np.float64)

        if self.rate_type == RateType.CALENDAR_DAY:
            rate_array = Rates.to_stream_day(
                calendar_day_rates=rate_array,
                regularity=self._regularity.values,
            )

        return rate_array.tolist()

    def get_stream_day_values(self) -> list[float]:
        """
        Returns the oil volume rate values as a list in stream day units.

        """
        return self._rate_values

    def get_periods(self) -> Periods:
        return self._time_series_expression.expression_evaluator.get_periods()


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
        name: str,
        component_type: ComponentType,
        emitter_type: VentingType,
        regularity: Regularity,
    ):
        self._uuid = id
        self._name = name
        self.component_type = component_type
        self.emitter_type = emitter_type
        self.regularity = regularity
        self.emission_results: dict[str, TimeSeriesStreamDayRate] | None = None

    def get_id(self) -> UUID:
        return self._uuid

    @property
    def name(self) -> str:
        return self._name

    def evaluate_emissions(
        self,
        energy_context: ComponentEnergyContext | None = None,
    ) -> dict[str, TimeSeriesStreamDayRate] | None:
        emission_rates = self._get_emissions()
        self.emission_results = emission_rates
        return emission_rates

    @abc.abstractmethod
    def _get_emissions(self) -> dict[str, TimeSeriesStreamDayRate]: ...

    def get_emissions(self) -> dict[EmissionName, TimeSeriesRate]:
        return {
            emission_name: TimeSeriesRate.from_timeseries_stream_day_rate(emission_rate, self.regularity.time_series)
            for emission_name, emission_rate in self._get_emissions().items()
        }

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
            emission_rate = emission.emission_rate.get_stream_day_values()
            unit = emission.emission_rate.unit
            emission_rate = unit.to(Unit.TONS_PER_DAY)(emission_rate)
            emissions[emission.name] = TimeSeriesStreamDayRate(
                periods=emission.emission_rate.get_periods(),
                values=emission_rate,
                unit=Unit.TONS_PER_DAY,
            )
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
            factors = self.volume.oil_volume_rate._time_series_expression.expression_evaluator.evaluate(
                Expression.setup_from_expression(value=emission.emission_factor)
            )

            emission_rate = [oil_rate * factor for oil_rate, factor in zip(oil_rates, factors)]
            emission_rate = Unit.KILO_PER_DAY.to(Unit.TONS_PER_DAY)(emission_rate)
            emissions[emission.name] = TimeSeriesStreamDayRate(
                periods=self.volume.oil_volume_rate.get_periods(),
                values=emission_rate,
                unit=Unit.TONS_PER_DAY,
            )
        return emissions

    def get_oil_rates(self) -> list[float]:
        oil_rates = self.volume.oil_volume_rate.get_stream_day_values()
        unit = self.volume.oil_volume_rate.unit
        oil_rates = unit.to(Unit.STANDARD_CUBIC_METER_PER_DAY)(oil_rates)

        return oil_rates

    def get_storage_rates(self) -> TimeSeriesRate:
        return TimeSeriesRate(
            periods=self.volume.oil_volume_rate.get_periods(),
            values=self.get_oil_rates(),
            unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
            regularity=self.regularity.values,
            rate_type=RateType.STREAM_DAY,
        )
