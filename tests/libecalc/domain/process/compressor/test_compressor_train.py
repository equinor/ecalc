import pytest
from inline_snapshot import snapshot

import libecalc.common.fixed_speed_pressure_control
from libecalc.common.serializable_chart import ChartCurveDTO, ChartDTO
from libecalc.domain.component_validation_error import ProcessChartTypeValidationException
from libecalc.domain.process.compressor.core.train.simplified_train import (
    CompressorTrainSimplifiedKnownStages,
    CompressorTrainSimplifiedUnknownStages,
)
from libecalc.domain.process.compressor.core.train.compressor_train_common_shaft import CompressorTrainCommonShaft
from libecalc.domain.process.entities.shaft import SingleSpeedShaft, Shaft
from libecalc.domain.process.value_objects.chart.generic import GenericChartFromDesignPoint, GenericChartFromInput
from libecalc.domain.process.value_objects.fluid_stream.fluid_model import EoSModel, FluidComposition, FluidModel
from libecalc.infrastructure.neqsim_fluid_provider.neqsim_fluid_factory import NeqSimFluidFactory
from libecalc.presentation.yaml.mappers.consumer_function_mapper import (
    _create_fluid_factory,
    _create_compressor_train_stage,
)


class TestCompressorTrainSimplified:
    def test_valid_train_unknown_stages(self, compressor_stages):
        """Testing that the "unknown stages" takes a "stage" argument, and not "stages"."""
        fluid_factory = _create_fluid_factory(
            FluidModel(eos_model=EoSModel.PR, composition=FluidComposition(methane=1))
        )
        stage = compressor_stages(
            chart=GenericChartFromInput(polytropic_efficiency_fraction=0.8),
            inlet_temperature_kelvin=300,
            remove_liquid_after_cooling=True,
        )[0]
        CompressorTrainSimplifiedUnknownStages(
            fluid_factory=fluid_factory,
            stage=stage,
            energy_usage_adjustment_factor=1,
            energy_usage_adjustment_constant=0,
            maximum_pressure_ratio_per_stage=3,
        )

    def test_valid_train_known_stages(self, compressor_stages):
        """Testing different chart types that are valid."""
        fluid_model = FluidModel(eos_model=EoSModel.PR, composition=FluidComposition(methane=1))
        stages = [
            compressor_stages(
                chart=GenericChartFromInput(polytropic_efficiency_fraction=1),
                inlet_temperature_kelvin=300,
                remove_liquid_after_cooling=True,
            )[0],
            compressor_stages(
                chart=GenericChartFromDesignPoint(
                    polytropic_efficiency_fraction=1,
                    design_polytropic_head_J_per_kg=1,
                    design_rate_actual_m3_per_hour=1,
                ),
                inlet_temperature_kelvin=300,
                remove_liquid_after_cooling=True,
            )[0],
            compressor_stages(
                chart=ChartDTO(
                    curves=[
                        ChartCurveDTO(
                            speed_rpm=1,
                            rate_actual_m3_hour=[1, 2],
                            polytropic_head_joule_per_kg=[3, 4],
                            efficiency_fraction=[0.5, 0.5],
                        )
                    ]
                ),
                inlet_temperature_kelvin=300,
                remove_liquid_after_cooling=True,
            )[0],
        ]
        CompressorTrainSimplifiedKnownStages(
            fluid_factory=NeqSimFluidFactory(fluid_model),
            stages=stages,
            energy_usage_adjustment_factor=1,
            energy_usage_adjustment_constant=0,
        )


class TestCompressorTrain:
    def test_valid_train_known_stages(self, compressor_stages):
        """Testing different chart types that are valid."""
        fluid_factory = _create_fluid_factory(
            FluidModel(eos_model=EoSModel.PR, composition=FluidComposition(methane=1))
        )
        stages = compressor_stages(
            chart=ChartDTO(
                curves=[
                    ChartCurveDTO(
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
            fluid_factory=fluid_factory,
            stages=stages,
            shaft=SingleSpeedShaft(),
            energy_usage_adjustment_factor=1,
            energy_usage_adjustment_constant=0,
            pressure_control=libecalc.common.fixed_speed_pressure_control.FixedSpeedPressureControl.DOWNSTREAM_CHOKE,
        )

    def test_invalid_chart(self, compressor_stages):
        """A compressor train does not support charts without speed curves"""
        with pytest.raises(ProcessChartTypeValidationException):
            fluid_factory = _create_fluid_factory(
                FluidModel(eos_model=EoSModel.PR, composition=FluidComposition(methane=1))
            )
            stages = compressor_stages(
                chart=ChartDTO(curves=[]),
                inlet_temperature_kelvin=300,
                remove_liquid_after_cooling=True,
            )
            CompressorTrainCommonShaft(
                fluid_factory=fluid_factory,
                stages=stages,
                energy_usage_adjustment_factor=1,
                energy_usage_adjustment_constant=0,
                pressure_control=libecalc.common.fixed_speed_pressure_control.FixedSpeedPressureControl.DOWNSTREAM_CHOKE,
            )

    def test_compatible_stages(self, compressor_stages):
        stages = [
            compressor_stages(
                chart=ChartDTO(
                    curves=[
                        ChartCurveDTO(
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
                chart=ChartDTO(
                    curves=[
                        ChartCurveDTO(
                            speed_rpm=1,
                            rate_actual_m3_hour=[1, 2, 3],
                            polytropic_head_joule_per_kg=[1, 2, 3],
                            efficiency_fraction=[0.1, 0.2, 0.3],
                        ),
                        ChartCurveDTO(
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
            fluid_factory=_create_fluid_factory(
                FluidModel(eos_model=EoSModel.PR, composition=FluidComposition(methane=1))
            ),
            stages=stages,
            shaft=SingleSpeedShaft(),
            energy_usage_adjustment_factor=1,
            energy_usage_adjustment_constant=0,
            pressure_control=libecalc.common.fixed_speed_pressure_control.FixedSpeedPressureControl.DOWNSTREAM_CHOKE,
        )

    @pytest.mark.snapshot
    @pytest.mark.inlinesnapshot
    def test_incompatible_stages(self, compressor_stages):
        stages = [
            compressor_stages(
                chart=ChartDTO(
                    curves=[
                        ChartCurveDTO(
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
                chart=ChartDTO(
                    curves=[
                        ChartCurveDTO(
                            speed_rpm=1,
                            rate_actual_m3_hour=[1, 2, 3],
                            polytropic_head_joule_per_kg=[1, 2, 3],
                            efficiency_fraction=[0.1, 0.2, 0.3],
                        ),
                        ChartCurveDTO(
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
                fluid_factory=_create_fluid_factory(
                    FluidModel(
                        eos_model=EoSModel.PR,
                        composition=FluidComposition(methane=1),
                    )
                ),
                stages=stages,
                shaft=Shaft,
                energy_usage_adjustment_factor=1,
                energy_usage_adjustment_constant=0,
                pressure_control=libecalc.common.fixed_speed_pressure_control.FixedSpeedPressureControl.DOWNSTREAM_CHOKE,
            )

        assert str(e.value) == snapshot(
            "Variable speed compressors in compressor train have incompatible compressor charts."
        )
