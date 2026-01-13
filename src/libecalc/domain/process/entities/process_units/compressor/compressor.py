from dataclasses import dataclass

from libecalc.common.errors.exceptions import IllegalStateException
from libecalc.common.logger import logger
from libecalc.domain.component_validation_error import ProcessCompressorEfficiencyValidationException
from libecalc.domain.process.compressor.core.train.utils.common import calculate_outlet_pressure_and_stream
from libecalc.domain.process.entities.shaft import Shaft
from libecalc.domain.process.value_objects.chart.chart import ChartData
from libecalc.domain.process.value_objects.chart.chart_area_flag import ChartAreaFlag
from libecalc.domain.process.value_objects.chart.compressor import CompressorChart
from libecalc.domain.process.value_objects.fluid_stream import FluidService, FluidStream


@dataclass
class OperationalPoint:
    actual_rate_m3_per_h: float
    polytropic_head_joule_per_kg: float
    polytropic_efficiency: float
    is_valid: bool


class Compressor:
    def __init__(self, compressor_chart: ChartData, fluid_service: FluidService, shaft: Shaft):
        self._compressor_chart = CompressorChart(compressor_chart)
        self._fluid_service = fluid_service
        self._shaft = shaft

        # Rate before asv is unset until assigned later
        self._rate_before_asv_m3_per_h: float | None = None

        # Operational point and chart area flag is unset until calculated and assigned later
        self._operational_point: OperationalPoint | None = None
        self._chart_area_flag: ChartAreaFlag | None = None

    @property
    def compressor_chart(self) -> CompressorChart:
        return self._compressor_chart

    @property
    def operational_point(self) -> OperationalPoint | None:
        """
        Returns the latest calculated operational point for the compressor.

        This represents the current state after the most recent chart calculation,
        or None if not yet set.
        """
        return self._operational_point

    @property
    def chart_area_flag(self) -> ChartAreaFlag | None:
        """
        Returns the latest calculated chart area flag for the compressor.

        This represents the current state after the most recent chart calculation,
        or None if not yet set.
        """
        return self._chart_area_flag

    @property
    def shaft(self) -> Shaft | None:
        return self._shaft

    @property
    def speed(self) -> float | None:
        if self.shaft is not None:
            return self.shaft.get_speed()
        return None

    def get_max_rate(self) -> float:
        assert self.speed is not None, "Speed must be set before getting max rate."
        return self.compressor_chart.maximum_rate_as_function_of_speed(self.speed)

    def get_min_rate(self) -> float:
        assert self.speed is not None, "Speed must be set before getting min rate."
        return self.compressor_chart.minimum_rate_as_function_of_speed(self.speed)

    def validate_speed(self):
        if self.speed is None or not (
            self.compressor_chart.minimum_speed <= self.speed <= self.compressor_chart.maximum_speed
        ):
            msg = f"Speed ({self.speed}) out of range ({self.compressor_chart.minimum_speed}-{self.compressor_chart.maximum_speed})."
            logger.exception(msg)
            raise IllegalStateException(msg)

    def set_rate_before_asv(self, rate_before_asv_m3_per_h: float):
        """
        Sets the volumetric flow rate before any ASV. Used for setting the chart area flag.
        """
        self._rate_before_asv_m3_per_h = rate_before_asv_m3_per_h

    def set_chart_area_flag_and_operational_point(
        self,
        actual_rate_m3_per_h_including_asv: float,
    ):
        assert self.speed is not None, "Speed must be set before calculating polytropic values."
        assert (
            self._rate_before_asv_m3_per_h is not None
        ), "Rate before ASV must be set before calculating chart area flag."

        chart_result = self.compressor_chart.calculate_polytropic_head_and_efficiency_single_point(
            speed=self.speed,
            actual_rate_m3_per_hour_including_asv=actual_rate_m3_per_h_including_asv,
            actual_rate_m3_per_hour=self._rate_before_asv_m3_per_h,
        )
        self._operational_point = OperationalPoint(
            actual_rate_m3_per_h=self._rate_before_asv_m3_per_h,
            polytropic_head_joule_per_kg=chart_result.polytropic_head,
            polytropic_efficiency=chart_result.polytropic_efficiency,
            is_valid=chart_result.is_valid,
        )
        self._chart_area_flag = chart_result.chart_area_flag

    def compress(self, inlet_stream: FluidStream) -> FluidStream:
        """
        Compresses the inlet fluid stream based on the polytropic efficiency and head.

        Args:
            inlet_stream: The incoming fluid stream to be compressed.

        Returns:
            FluidStream: The compressed fluid stream with updated pressure and temperature.
        """
        self.set_chart_area_flag_and_operational_point(
            actual_rate_m3_per_h_including_asv=inlet_stream.volumetric_rate_m3_per_hour,
        )

        if self.operational_point.polytropic_efficiency == 0.0:
            raise ProcessCompressorEfficiencyValidationException("Efficiency from compressor chart is 0.")

        assert self.operational_point is not None, "Operational point must be set before compression."

        return calculate_outlet_pressure_and_stream(
            polytropic_efficiency=self.operational_point.polytropic_efficiency,
            polytropic_head_joule_per_kg=self.operational_point.polytropic_head_joule_per_kg,
            inlet_stream=inlet_stream,
            fluid_service=self._fluid_service,
        )
