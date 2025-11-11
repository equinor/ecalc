import pytest
from inline_snapshot import snapshot

import libecalc.common.fixed_speed_pressure_control
from libecalc.domain.component_validation_error import ProcessChartTypeValidationException
from libecalc.domain.process.compressor.core.train.compressor_train_common_shaft import CompressorTrainCommonShaft
from libecalc.domain.process.entities.shaft import Shaft, SingleSpeedShaft


class TestCompressorTrain:
    def test_valid_train_known_stages(self, compressor_stages, chart_data_factory, chart_curve_factory):
        """Testing different chart types that are valid."""
        stages = compressor_stages(
            chart=chart_data_factory.from_curves(
                curves=[
                    chart_curve_factory(
                        speed_rpm=1,
                        rate_actual_m3_hour=[1, 2],
                        polytropic_head_joule_per_kg=[3, 4],
                        efficiency_fraction=[0.5, 0.5],
                    )
                ]
            ),
            inlet_temperature_kelvin=300,
            remove_liquid_after_cooling=True,
        )

        CompressorTrainCommonShaft(
            stages=stages,
            shaft=SingleSpeedShaft(),
            energy_usage_adjustment_factor=1,
            energy_usage_adjustment_constant=0,
            pressure_control=libecalc.common.fixed_speed_pressure_control.FixedSpeedPressureControl.DOWNSTREAM_CHOKE,
        )

    def test_compatible_stages(self, compressor_stages, chart_data_factory, chart_curve_factory):
        stages = [
            compressor_stages(
                chart=chart_data_factory.from_curves(
                    curves=[
                        chart_curve_factory(
                            speed_rpm=1,
                            rate_actual_m3_hour=[1, 2, 3],
                            polytropic_head_joule_per_kg=[1, 2, 3],
                            efficiency_fraction=[0.1, 0.2, 0.3],
                        )
                    ],
                ),
                inlet_temperature_kelvin=300,
                remove_liquid_after_cooling=True,
            )[0],
            compressor_stages(
                chart=chart_data_factory.from_curves(
                    curves=[
                        chart_curve_factory(
                            speed_rpm=1,
                            rate_actual_m3_hour=[1, 2, 3],
                            polytropic_head_joule_per_kg=[1, 2, 3],
                            efficiency_fraction=[0.1, 0.2, 0.3],
                        ),
                        chart_curve_factory(
                            speed_rpm=2,
                            rate_actual_m3_hour=[1, 2, 3],
                            polytropic_head_joule_per_kg=[1, 2, 3],
                            efficiency_fraction=[0.1, 0.2, 0.3],
                        ),
                    ],
                ),
                inlet_temperature_kelvin=300,
            )[0],
        ]
        CompressorTrainCommonShaft(
            stages=stages,
            shaft=SingleSpeedShaft(),
            energy_usage_adjustment_factor=1,
            energy_usage_adjustment_constant=0,
            pressure_control=libecalc.common.fixed_speed_pressure_control.FixedSpeedPressureControl.DOWNSTREAM_CHOKE,
        )

    @pytest.mark.snapshot
    @pytest.mark.inlinesnapshot
    def test_incompatible_stages(self, compressor_stages, chart_data_factory, chart_curve_factory):
        stages = [
            compressor_stages(
                chart=chart_data_factory.from_curves(
                    curves=[
                        chart_curve_factory(
                            speed_rpm=3,
                            rate_actual_m3_hour=[1, 2, 3],
                            polytropic_head_joule_per_kg=[1, 2, 3],
                            efficiency_fraction=[0.1, 0.2, 0.3],
                        )
                    ],
                ),
                inlet_temperature_kelvin=300,
                remove_liquid_after_cooling=True,
            )[0],
            compressor_stages(
                chart=chart_data_factory.from_curves(
                    curves=[
                        chart_curve_factory(
                            speed_rpm=1,
                            rate_actual_m3_hour=[1, 2, 3],
                            polytropic_head_joule_per_kg=[1, 2, 3],
                            efficiency_fraction=[0.1, 0.2, 0.3],
                        ),
                        chart_curve_factory(
                            speed_rpm=2,
                            rate_actual_m3_hour=[1, 2, 3],
                            polytropic_head_joule_per_kg=[1, 2, 3],
                            efficiency_fraction=[0.1, 0.2, 0.3],
                        ),
                    ],
                ),
                inlet_temperature_kelvin=300,
                remove_liquid_after_cooling=False,
            )[0],
        ]
        with pytest.raises(ProcessChartTypeValidationException) as e:
            CompressorTrainCommonShaft(
                stages=stages,
                shaft=Shaft,
                energy_usage_adjustment_factor=1,
                energy_usage_adjustment_constant=0,
                pressure_control=libecalc.common.fixed_speed_pressure_control.FixedSpeedPressureControl.DOWNSTREAM_CHOKE,
            )

        assert str(e.value) == snapshot(
            "Variable speed compressors in compressor train have incompatible compressor charts."
        )
