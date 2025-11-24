from functools import cached_property

import numpy as np

from libecalc.common.chart_type import ChartType
from libecalc.domain.process.compressor.core.train.utils.enthalpy_calculations import (
    calculate_enthalpy_change_head_iteration,
)
from libecalc.domain.process.value_objects.chart import ChartCurve
from libecalc.domain.process.value_objects.chart.chart import ChartData
from libecalc.domain.process.value_objects.chart.compressor.chart_creator import CompressorChartCreator
from libecalc.domain.process.value_objects.fluid_stream.fluid_factory import FluidFactoryInterface


class GenericFromInputChartData(ChartData):
    def __init__(
        self,
        fluid_factory: FluidFactoryInterface,
        standard_rates: list[float],
        inlet_temperature: float,
        inlet_pressure: list[float],
        polytropic_efficiency: float,
        outlet_pressure: list[float],
    ):
        self._fluid_factory = fluid_factory
        self._standard_rates = standard_rates
        self._inlet_pressure = inlet_pressure
        self._inlet_temperature = inlet_temperature
        self._polytropic_efficiency = polytropic_efficiency
        self._outlet_pressure = outlet_pressure

    @cached_property
    def _chart(self) -> ChartData:
        inlet_streams = [
            self._fluid_factory.create_stream_from_standard_rate(
                pressure_bara=inlet_pressure,
                temperature_kelvin=self._inlet_temperature,
                standard_rate_m3_per_day=inlet_rate,
            )
            for inlet_rate, inlet_pressure in zip(self._standard_rates, self._inlet_pressure)
        ]

        # Static efficiency regardless of rate and head
        def efficiency_as_function_of_rate_and_head(rates, heads):
            return np.full_like(rates, fill_value=self._polytropic_efficiency, dtype=float)

        polytropic_enthalpy_change_joule_per_kg, polytropic_efficiency = calculate_enthalpy_change_head_iteration(
            inlet_streams=inlet_streams,
            outlet_pressure=np.asarray(self._outlet_pressure),
            polytropic_efficiency_vs_rate_and_head_function=efficiency_as_function_of_rate_and_head,
        )

        head_joule_per_kg = polytropic_enthalpy_change_joule_per_kg * polytropic_efficiency
        inlet_actual_rate_m3_per_hour = np.asarray([stream.volumetric_rate for stream in inlet_streams])

        # Convert numpy arrays to lists for proper type annotation
        actual_rates_list: list[float] = inlet_actual_rate_m3_per_hour.astype(float).tolist()

        # Handle union type for head_joule_per_kg
        if isinstance(head_joule_per_kg, np.ndarray):
            heads_list: list[float] = head_joule_per_kg.astype(float).tolist()
        else:
            heads_list = [float(head_joule_per_kg)]

        return CompressorChartCreator.from_rate_and_head_values(
            actual_volume_rates_m3_per_hour=actual_rates_list,
            heads_joule_per_kg=heads_list,
            polytropic_efficiency=self._polytropic_efficiency,
        )

    def get_original_curves(self) -> list[ChartCurve]:
        return self._chart.get_original_curves()

    def get_adjusted_curves(self) -> list[ChartCurve]:
        return self.get_original_curves()  # No adjustment in generic charts

    @property
    def origin_of_chart_data(self) -> ChartType:
        return ChartType.GENERIC_FROM_INPUT

    @property
    def design_head(self):
        return self._chart.design_head

    @property
    def design_rate(self):
        return self._chart.design_rate
