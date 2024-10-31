from typing import Annotated, Optional

from pydantic import Field

from libecalc.common.fixed_speed_pressure_control import FixedSpeedPressureControl
from libecalc.common.serializable_chart import VariableSpeedChartDTO
from libecalc.dto.base import EcalcBaseModel
from libecalc.dto.models.compressor.chart import CompressorChart


class CompressorStage(EcalcBaseModel):
    compressor_chart: CompressorChart
    inlet_temperature_kelvin: Annotated[float, Field(ge=0)]
    pressure_drop_before_stage: Annotated[float, Field(ge=0)]
    remove_liquid_after_cooling: bool
    control_margin: Annotated[float, Field(ge=0, le=1)] = 0.0  # Todo: this probably belong to the chart, not the stage.


class InterstagePressureControl(EcalcBaseModel):
    upstream_pressure_control: FixedSpeedPressureControl
    downstream_pressure_control: FixedSpeedPressureControl


class MultipleStreamsCompressorStage(CompressorStage):
    """Special case for multiple streams model."""

    compressor_chart: VariableSpeedChartDTO
    stream_reference: Optional[list[str]] = None
    interstage_pressure_control: Optional[InterstagePressureControl] = None

    @property
    def has_control_pressure(self):
        return self.interstage_pressure_control is not None
