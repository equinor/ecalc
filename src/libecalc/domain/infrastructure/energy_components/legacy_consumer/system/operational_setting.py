from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import NDArray

from libecalc.common.logger import logger
from libecalc.domain.component_validation_error import DomainValidationException
from libecalc.domain.time_series_flow_rate import TimeSeriesFlowRate
from libecalc.domain.time_series_fluid_density import TimeSeriesFluidDensity
from libecalc.domain.time_series_pressure import TimeSeriesPressure


class ConsumerSystemOperationalSettingExpressions:
    """Each index of a setting is aligned with a consumer. The first consumer has rate self.rates[0], etc.

    cross_overs: Defines what consumer to send exceeding rates to (Warning! index starts at 1!).
        - 0 means no cross-over.
        - 1 means send exceeding rate (above max rate) to the first consumer
        - 2 means send exceeding rate (above max rate) to the second consumer

    E.g. [3, 3, 0]: First and second consumer sends exceeding rate to the thirds consumer. Third consumer does not
        have the ability to send exceeding rates anywhere.

    Note that circular references is not possible.
    """

    def __init__(
        self,
        rates: list[TimeSeriesFlowRate],
        suction_pressures: list[TimeSeriesPressure],
        discharge_pressures: list[TimeSeriesPressure],
        cross_overs: list[int] | None = None,
        fluid_densities: list[TimeSeriesFluidDensity] | None = None,
    ):
        self._rates = rates
        self.suction_pressures = suction_pressures
        self.discharge_pressures = discharge_pressures
        self.cross_overs = cross_overs
        self.fluid_densities = fluid_densities
        self.check_list_length()
        self._rates_after_crossover = None

    @property
    def number_of_consumers(self):
        return len(self.rates)

    @property
    def rates(self) -> list[TimeSeriesFlowRate]:
        return self._rates

    def set_rates_after_crossover(self, rates_after_crossover: list[NDArray[np.float64]]):
        self._rates_after_crossover = rates_after_crossover

    def get_rate(self, consumer_index: int) -> NDArray[np.float64]:
        return np.asarray(self._rates[consumer_index].get_stream_day_values())

    def get_rate_after_crossover(self, consumer_index: int) -> NDArray[np.float64]:
        return (
            self._rates_after_crossover[consumer_index]
            if self._rates_after_crossover is not None
            else self.get_rate(consumer_index)
        )

    def get_crossover_rate(self, consumer_index: int) -> NDArray[np.float64]:
        return self.get_rate_after_crossover(consumer_index) - self.get_rate(consumer_index)

    def get_suction_pressure(self, consumer_index: int) -> NDArray[np.float64]:
        return np.asarray(self.suction_pressures[consumer_index].get_values())

    def get_discharge_pressure(self, consumer_index: int) -> NDArray[np.float64]:
        return np.asarray(self.discharge_pressures[consumer_index].get_values())

    def get_fluid_density(self, consumer_index: int) -> NDArray[np.float64]:
        return np.asarray(self.fluid_densities[consumer_index].get_values()) if self.fluid_densities is not None else 1

    def check_list_length(self):
        def _log_error(field: str, field_values: list[Any], n_rates) -> None:
            msg = (
                f"All attributes in a consumer system operational setting must have the same number of elements"
                f"(corresponding to the number of consumers). The number of elements in {field} "
                f"({len(field_values)}) is not equal to the number of elements in rates ({n_rates})."
            )
            logger.error(msg)
            raise DomainValidationException(message=msg)

        rates = self.rates
        suction_pressures = self.suction_pressures
        discharge_pressures = self.discharge_pressures
        cross_overs = self.cross_overs
        n_rates = len(rates)

        if len(suction_pressures) != n_rates:
            _log_error(field="suction_pressures", field_values=suction_pressures, n_rates=n_rates)
        if len(discharge_pressures) != n_rates:
            _log_error(field="discharge_pressures", field_values=discharge_pressures, n_rates=n_rates)
        if cross_overs and len(cross_overs) != n_rates:
            _log_error(field="cross_overs", field_values=cross_overs, n_rates=n_rates)
        return self
