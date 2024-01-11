from typing import List, Optional

from pydantic import Field
from typing_extensions import Annotated

from libecalc.dto.base import EcalcBaseModel
from libecalc.dto.models.compressor.chart import CompressorChart, VariableSpeedChart
from libecalc.dto.types import FixedSpeedPressureControl


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

    compressor_chart: VariableSpeedChart
    stream_reference: Optional[List[str]] = None
    interstage_pressure_control: Optional[InterstagePressureControl] = None

    @property
    def has_control_pressure(self):
        return self.interstage_pressure_control is not None
