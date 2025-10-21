import numpy as np

from libecalc.domain.infrastructure.energy_components.legacy_consumer.consumer_function import (
    ConsumerFunction,
    ConsumerFunctionResult,
)
from libecalc.domain.process.pump.pump import PumpModel
from libecalc.domain.time_series_flow_rate import TimeSeriesFlowRate
from libecalc.domain.time_series_fluid_density import TimeSeriesFluidDensity
from libecalc.domain.time_series_power_loss_factor import TimeSeriesPowerLossFactor
from libecalc.domain.time_series_pressure import TimeSeriesPressure


class PumpConsumerFunction(ConsumerFunction):
    """
    The pump consumer function defining the energy usage.

    Args:
        pump_function: The pump model
        fluid_density (TimeSeriesFluidDensity): Fluid density time series [kg/m3]
        rate (TimeSeriesFlowRate): Flow rate time series [Sm3/h].
        suction_pressure (TimeSeriesPressure): Suction pressure time series [bara].
        discharge_pressure (TimeSeriesPressure): Discharge pressure time series [bara].
        power_loss_factor(TimeSeriesPowerLossFactor): Power loss factor time series.
            Typically used for power line loss subsea et.c.
    """

    def __init__(
        self,
        pump_function: PumpModel,
        rate: TimeSeriesFlowRate,
        suction_pressure: TimeSeriesPressure,
        discharge_pressure: TimeSeriesPressure,
        fluid_density: TimeSeriesFluidDensity,
        power_loss_factor: TimeSeriesPowerLossFactor | None = None,
    ):
        self._pump_function = pump_function
        self._rate = rate
        self._fluid_density = fluid_density
        self._suction_pressure = suction_pressure
        self._discharge_pressure = discharge_pressure

        # Typically used for power line loss subsea et.c.
        self._power_loss_factor = power_loss_factor

    def evaluate(self) -> ConsumerFunctionResult:
        """Evaluate the pump consumer function

        Returns:
            Pump consumer function result
        """

        stream_day_rate = self._rate.get_stream_day_values()

        # Do not input regularity to pump function. Handled outside
        energy_function_result = self._pump_function.evaluate_rate_ps_pd_density(
            rates=np.asarray(stream_day_rate, dtype=np.float64),
            suction_pressures=np.asarray(self._suction_pressure.get_values(), dtype=np.float64),
            discharge_pressures=np.asarray(self._discharge_pressure.get_values(), dtype=np.float64),
            fluid_densities=np.asarray(self._fluid_density.get_values(), dtype=np.float64),
        )

        pump_consumer_function_result = ConsumerFunctionResult(
            periods=self._rate.get_periods(),
            energy_function_result=energy_function_result,
            power_loss_factor=self._power_loss_factor,
        )
        return pump_consumer_function_result
