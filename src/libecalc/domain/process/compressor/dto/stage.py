from libecalc.common.fixed_speed_pressure_control import FixedSpeedPressureControl


class InterstagePressureControl:
    def __init__(
        self,
        upstream_pressure_control: FixedSpeedPressureControl,
        downstream_pressure_control: FixedSpeedPressureControl,
    ):
        self.upstream_pressure_control = upstream_pressure_control
        self.downstream_pressure_control = downstream_pressure_control
