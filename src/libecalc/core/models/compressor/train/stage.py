from typing import Dict, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing_extensions import Annotated

from libecalc import dto
from libecalc.common.errors.exceptions import IllegalStateException
from libecalc.common.logger import logger
from libecalc.core.models.compressor.results import (
    CompressorTrainStageResultSingleTimeStep,
)
from libecalc.core.models.compressor.train.chart import (
    SingleSpeedCompressorChart,
    VariableSpeedCompressorChart,
)
from libecalc.core.models.compressor.train.fluid import FluidStream
from libecalc.core.models.compressor.train.utils.common import (
    calculate_asv_corrected_rate,
    calculate_outlet_pressure_and_stream,
    calculate_power_in_megawatt,
)


class CompressorTrainStage(BaseModel):
    """inlet_temperature_kelvin [K].

    Note: Used in both Single and Variable Speed compressor process modelling.
    """

    compressor_chart: Union[SingleSpeedCompressorChart, VariableSpeedCompressorChart]
    inlet_temperature_kelvin: float
    remove_liquid_after_cooling: bool
    pressure_drop_ahead_of_stage: Optional[float] = None
    model_config = ConfigDict(arbitrary_types_allowed=True)

    def evaluate(
        self,
        inlet_stream_stage: FluidStream,
        mass_rate_kg_per_hour: float,
        speed: Optional[float] = None,
        asv_rate_fraction: Optional[float] = 0.0,
        asv_additional_mass_rate: Optional[float] = 0.0,
        increase_rate_left_of_minimum_flow_assuming_asv: Optional[bool] = True,
        increase_speed_below_assuming_choke: Optional[bool] = False,
    ) -> CompressorTrainStageResultSingleTimeStep:
        """Evaluates a compressor train stage given the conditions and rate of the inlet stream, and the speed
        of the shaft driving the compressor if given.

        :param inlet_stream_stage: The conditions of the inlet fluid stream
        :param mass_rate_kg_per_hour: The mass rate (kg pr hour) entering the compressor stage
        :param speed: The speed of the shaft driving the compressor (a single speed compressor will only have on speed)
        :param asv_rate_fraction: Fraction of the available capacity of the compressor to fill using some kind of
            pressure control (on the interval [0,1]).
        :param asv_additional_mass_rate: Additional recirculated mass rate due to pressure control

        Note: asv_rate_fraction and asv_additional_mass_rate can not be defined different from zero at the same time

        Returns: Results of the evaluation
        """
        if isinstance(self.compressor_chart, VariableSpeedCompressorChart):
            if speed is None:
                msg = (
                    f"Speed value ({speed}) is not allowed for a variable speed compressor chart."
                    f"You should not end up here, please contact support."
                )
                logger.exception(msg)
                raise IllegalStateException(msg)

            if speed < self.compressor_chart.minimum_speed or speed > self.compressor_chart.maximum_speed:
                msg = (
                    f"Speed value ({speed}) outside allowed range ({self.compressor_chart.minimum_speed} -"
                    f" {self.compressor_chart.maximum_speed}). You should not end up here, please contact support."
                )
                logger.exception(msg)
                raise IllegalStateException(msg)

        if asv_rate_fraction is not None and asv_additional_mass_rate is not None:
            if asv_rate_fraction > 0 and asv_additional_mass_rate > 0:
                msg = "asv_rate_fraction and asv_additional_mass_rate can not both be larger than 0"
                logger.exception(msg)
                raise IllegalStateException(msg)
            if asv_rate_fraction < 0.0 or asv_rate_fraction > 1.0:
                msg = "asv rate fraction must be a number in the interval [0.0, 1.0]"
                logger.exception(msg)
                raise IllegalStateException(msg)

        if self.pressure_drop_ahead_of_stage:
            inlet_pressure_stage = inlet_stream_stage.pressure_bara - self.pressure_drop_ahead_of_stage
        else:
            inlet_pressure_stage = inlet_stream_stage.pressure_bara

        inlet_stream_compressor = inlet_stream_stage.set_new_pressure_and_temperature(
            new_pressure_bara=inlet_pressure_stage,
            new_temperature_kelvin=self.inlet_temperature_kelvin,
            remove_liquid=self.remove_liquid_after_cooling,
        )
        # Inlet stream/fluid properties
        inlet_density_kg_per_m3 = inlet_stream_compressor.density

        actual_rate_m3_per_hour_to_use = actual_rate_m3_per_hour = mass_rate_kg_per_hour / inlet_density_kg_per_m3
        compressor_maximum_actual_rate_m3_per_hour = (
            self.compressor_chart.maximum_rate_as_function_of_speed(speed)
            if isinstance(self.compressor_chart, VariableSpeedCompressorChart)
            else self.compressor_chart.maximum_rate
        )

        additional_rate_m3_per_hour = 0.0
        # Add contribution from asv_rate_fraction (potentially used for pressure control)
        if asv_rate_fraction:
            additional_rate_m3_per_hour = asv_rate_fraction * (
                compressor_maximum_actual_rate_m3_per_hour - actual_rate_m3_per_hour
            )
        # Add contribution from asv_additional_mass_rate (potentially used for pressure control)
        if asv_additional_mass_rate:
            additional_rate_m3_per_hour = asv_additional_mass_rate / inlet_density_kg_per_m3

        if isinstance(self.compressor_chart, VariableSpeedCompressorChart):
            compressor_chart_head_and_efficiency_result = (
                self.compressor_chart.calculate_polytropic_head_and_efficiency_single_point(
                    speed=speed,
                    actual_rate_m3_per_hour=actual_rate_m3_per_hour,
                    recirculated_rate_m3_per_hour=additional_rate_m3_per_hour,
                    increase_rate_left_of_minimum_flow_assuming_asv=increase_rate_left_of_minimum_flow_assuming_asv,
                    increase_speed_below_assuming_choke=increase_speed_below_assuming_choke,
                )
            )
        else:
            compressor_chart_head_and_efficiency_result = (
                self.compressor_chart.calculate_polytropic_head_and_efficiency_single_point(
                    actual_rate_m3_per_hour=actual_rate_m3_per_hour,
                    recirculated_rate_m3_per_hour=additional_rate_m3_per_hour,
                    increase_rate_left_of_minimum_flow_assuming_asv=increase_rate_left_of_minimum_flow_assuming_asv,
                )
            )

        actual_rate_m3_per_hour_to_use += additional_rate_m3_per_hour

        polytropic_head_J_per_kg = compressor_chart_head_and_efficiency_result.polytropic_head
        polytropic_efficiency = compressor_chart_head_and_efficiency_result.polytropic_efficiency
        chart_area_flag = compressor_chart_head_and_efficiency_result.chart_area_flag

        if polytropic_efficiency == 0.0:
            raise ValueError("Division by zero error. Efficiency from compressor chart is 0.")

        # Enthalpy change
        enthalpy_change_J_per_kg = polytropic_head_J_per_kg / polytropic_efficiency

        (
            actual_rate_asv_corrected_m3_per_hour,
            mass_rate_asv_corrected_kg_per_hour,
        ) = calculate_asv_corrected_rate(
            minimum_actual_rate_m3_per_hour=self.compressor_chart.minimum_rate_as_function_of_speed(speed)
            if isinstance(self.compressor_chart, VariableSpeedCompressorChart)
            else self.compressor_chart.minimum_rate,
            actual_rate_m3_per_hour=actual_rate_m3_per_hour_to_use,
            density_kg_per_m3=inlet_density_kg_per_m3,
        )
        power_megawatt = calculate_power_in_megawatt(
            enthalpy_change_joule_per_kg=enthalpy_change_J_per_kg,
            mass_rate_kg_per_hour=mass_rate_asv_corrected_kg_per_hour,
        )

        (
            outlet_pressure_this_stage_bara,
            outlet_stream,
        ) = calculate_outlet_pressure_and_stream(
            polytropic_efficiency=polytropic_efficiency,
            polytropic_head_joule_per_kg=polytropic_head_J_per_kg,
            inlet_stream=inlet_stream_compressor,
        )

        return CompressorTrainStageResultSingleTimeStep(
            inlet_stream=dto.FluidStream.from_fluid_domain_object(fluid_stream=inlet_stream_compressor),
            outlet_stream=dto.FluidStream.from_fluid_domain_object(fluid_stream=outlet_stream),
            inlet_actual_rate_m3_per_hour=mass_rate_kg_per_hour / inlet_stream_compressor.density,
            inlet_actual_rate_asv_corrected_m3_per_hour=mass_rate_asv_corrected_kg_per_hour
            / inlet_stream_compressor.density,
            outlet_actual_rate_m3_per_hour=mass_rate_kg_per_hour / outlet_stream.density,
            outlet_actual_rate_asv_corrected_m3_per_hour=mass_rate_asv_corrected_kg_per_hour / outlet_stream.density,
            mass_rate_kg_per_hour=mass_rate_kg_per_hour,
            mass_rate_asv_corrected_kg_per_hour=mass_rate_asv_corrected_kg_per_hour,
            polytropic_head_kJ_per_kg=polytropic_head_J_per_kg / 1000,
            polytropic_efficiency=polytropic_efficiency,
            chart_area_flag=chart_area_flag,
            polytropic_enthalpy_change_kJ_per_kg=enthalpy_change_J_per_kg / 1000,
            power_megawatt=power_megawatt,
            point_is_valid=compressor_chart_head_and_efficiency_result.is_valid,
            polytropic_enthalpy_change_before_choke_kJ_per_kg=enthalpy_change_J_per_kg / 1000,
            inlet_pressure_before_choking=inlet_stream_compressor.pressure_bara,
            outlet_pressure_before_choking=outlet_stream.pressure_bara,
        )


class UndefinedCompressorStage(CompressorTrainStage):
    """A stage without a defined compressor chart is 'undefined'.

    Artifact of the 'Generic from Input' chart.
    """

    polytropic_efficiency: Annotated[float, Field(gt=0, le=1)]

    # Not in use:
    compressor_chart: VariableSpeedCompressorChart = None  # Not relevant when undefined.

    @model_validator(mode="before")
    def validate_predefined_chart(cls, v: Dict):
        if v.get("compressor_chart") is None and v.get("polytropic_efficiency") is None:
            raise ValueError("Stage with non-predefined compressor chart needs to have polytropic_efficiency")
        return v
