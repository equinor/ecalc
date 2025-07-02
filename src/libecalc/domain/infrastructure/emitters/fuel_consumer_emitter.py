import abc
import logging
from collections import defaultdict
from typing import TypeVar, cast

from libecalc.common.time_utils import Period
from libecalc.common.units import Unit
from libecalc.common.utils.rates import TimeSeriesStreamDayRate
from libecalc.domain.common.entity_id import ID
from libecalc.domain.energy import ComponentEnergyContext, Emitter, EnergyModel

logger = logging.getLogger(__name__)

EmissionName = str


class EmissionFactors(abc.ABC):
    @abc.abstractmethod
    def get_emissions(self) -> list[EmissionName]: ...

    @abc.abstractmethod
    def get_emission_factor(self, emission_name: str, period: Period) -> float: ...


ID_T = TypeVar("ID_T", bound=ID)


class FuelConsumerEmitter(Emitter[ID_T]):
    def __init__(self, entity_id: ID_T, emissions: EmissionFactors):
        super().__init__(entity_id=entity_id)
        self._emissions = emissions

    @property
    def id(self) -> str:
        return self.get_id().get_name()

    def evaluate_emissions(
        self,
        energy_context: ComponentEnergyContext,
        energy_model: EnergyModel,
    ) -> dict[str, TimeSeriesStreamDayRate] | None:
        fuel_usage = energy_context.get_fuel_usage()

        assert fuel_usage is not None

        logger.debug("Evaluating fuel usage and emissions")

        emission_rates_kg_per_day = defaultdict(list)

        for emission_name in self._emissions.get_emissions():
            for period, fuel_rate in fuel_usage.datapoints():
                factor = self._emissions.get_emission_factor(emission_name, period)
                emission_rate_kg_per_day = fuel_rate * factor
                emission_rates_kg_per_day[emission_name].append(emission_rate_kg_per_day)

        return {
            emission_name: TimeSeriesStreamDayRate(
                periods=fuel_usage.periods,
                values=cast(list[float], emission_rate),
                unit=Unit.KILO_PER_DAY,
            )
            for emission_name, emission_rate in sorted(emission_rates_kg_per_day.items())
        }
