from typing import List, Optional, Union

from libecalc.dto.base import EcalcBaseModel
from libecalc.dto.models.compressor.chart import CompressorChart, VariableSpeedChart
from libecalc.dto.types import FixedSpeedPressureControl
from libecalc.expression import Expression
from pydantic import confloat


class CompressorStage(EcalcBaseModel):
    compressor_chart: CompressorChart
    inlet_temperature_kelvin: confloat(ge=0)
    pressure_drop_before_stage: Union[str, confloat(ge=0), Expression, List[Expression]]
    remove_liquid_after_cooling: bool
    control_margin: confloat(ge=0, le=1) = 0.0  # Todo: this probably belong to the chart, not the stage.


class InterstagePressureControl(EcalcBaseModel):
    upstream_pressure_control: FixedSpeedPressureControl
    downstream_pressure_control: FixedSpeedPressureControl


class MultipleStreamsCompressorStage(CompressorStage):
    """Special case for multiple streams model."""

    compressor_chart: VariableSpeedChart
    stream_reference: Optional[List[str]]
    interstage_pressure_control: Optional[InterstagePressureControl]

    @property
    def has_control_pressure(self):
        return self.interstage_pressure_control is not None
