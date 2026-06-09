"""Shared fixtures for the compressor solver-path matrix suites."""

from __future__ import annotations

import pytest

from libecalc.common.fixed_speed_pressure_control import FixedSpeedPressureControl
from libecalc.domain.process.compressor.core.train.compressor_train_common_shaft import CompressorTrainCommonShaft
from libecalc.domain.process.compressor.core.train.stage import CompressorTrainStage
from libecalc.domain.process.value_objects.chart.chart import ChartData

INLET_TEMPERATURE_KELVIN = 303.15


@pytest.fixture
def legacy_train_factory(compressor_stage_factory, fluid_service, pure_methane_fluid_model):
    def create_legacy_train(
        chart_data: ChartData,
        pressure_control: FixedSpeedPressureControl | None,
    ) -> CompressorTrainCommonShaft:
        from libecalc.process.shaft import VariableSpeedShaft

        shaft = VariableSpeedShaft()
        stage: CompressorTrainStage = compressor_stage_factory(
            shaft=shaft,
            compressor_chart_data=chart_data,
            inlet_temperature_kelvin=INLET_TEMPERATURE_KELVIN,
            remove_liquid_after_cooling=True,
            pressure_drop_ahead_of_stage=0.0,
        )
        train = CompressorTrainCommonShaft(
            shaft=shaft,
            fluid_service=fluid_service,
            energy_usage_adjustment_constant=0,
            energy_usage_adjustment_factor=1,
            stages=[stage],
            pressure_control=pressure_control,
            calculate_max_rate=False,
        )
        train._fluid_model = [pure_methane_fluid_model]
        return train

    return create_legacy_train
