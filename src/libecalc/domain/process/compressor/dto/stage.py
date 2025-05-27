from libecalc.common.fixed_speed_pressure_control import FixedSpeedPressureControl
from libecalc.domain.process.chart.compressor.compressor_chart_dto import CompressorChart


class InterstagePressureControl:
    def __init__(
        self,
        upstream_pressure_control: FixedSpeedPressureControl,
        downstream_pressure_control: FixedSpeedPressureControl,
    ):
        self.upstream_pressure_control = upstream_pressure_control
        self.downstream_pressure_control = downstream_pressure_control


class CompressorStage:
    """Special case for multiple streams model."""

    def __init__(
        self,
        compressor_chart: CompressorChart,
        inlet_temperature_kelvin: float,
        pressure_drop_before_stage: float,
        remove_liquid_after_cooling: bool,
        stream_reference: list[str] | None = None,
        interstage_pressure_control: InterstagePressureControl | None = None,
        control_margin: float = 0.0,
    ):
        if inlet_temperature_kelvin < 0:
            raise ValueError("inlet_temperature_kelvin must be greater than or equal to 0")
        if pressure_drop_before_stage < 0:
            raise ValueError("pressure_drop_before_stage must be greater than or equal to 0")
        if not (0 <= control_margin <= 1):
            raise ValueError("control_margin must be between 0 and 1")

        self.compressor_chart = compressor_chart
        self.inlet_temperature_kelvin = inlet_temperature_kelvin
        self.pressure_drop_before_stage = pressure_drop_before_stage
        self.remove_liquid_after_cooling = remove_liquid_after_cooling
        self.control_margin = control_margin
        self.stream_reference = stream_reference
        self.interstage_pressure_control = interstage_pressure_control

    @property
    def has_control_pressure(self):
        return self.interstage_pressure_control is not None
