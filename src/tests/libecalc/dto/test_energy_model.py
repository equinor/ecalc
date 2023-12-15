import pytest
from libecalc import dto

try:
    from pydantic.v1 import ValidationError
except ImportError:
    from pydantic import ValidationError


class TestTurbine:
    def test_turbine(self):
        dto.Turbine(
            lower_heating_value=38,
            turbine_loads=[0, 2.352, 4.589, 6.853, 9.125, 11.399, 13.673, 15.947, 18.223, 20.496, 22.767],
            turbine_efficiency_fractions=[0, 0.138, 0.21, 0.255, 0.286, 0.31, 0.328, 0.342, 0.353, 0.36, 0.362],
            energy_usage_adjustment_constant=0,
            energy_usage_adjustment_factor=0,
        )

    def test_unequal_load_and_efficiency_lengths(self):
        with pytest.raises(ValidationError) as e:
            dto.Turbine(
                lower_heating_value=38,
                turbine_loads=[0, 2.352, 4.589, 6.853, 9.125, 11.399, 13.673, 15.947, 18.223, 20.496],
                turbine_efficiency_fractions=[0, 0.138, 0.21, 0.255, 0.286, 0.31, 0.328, 0.342, 0.353, 0.36, 0.362],
                energy_usage_adjustment_constant=0,
                energy_usage_adjustment_factor=1.0,
            )
        assert e.value.raw_errors[0].exc.args[0] == "Need equal number of load and efficiency values for turbine model"


class TestVariableSpeedCompressorChart:
    def test_variable_speed_compressor_chart(self):
        dto.VariableSpeedChart(
            curves=[
                dto.ChartCurve(
                    speed_rpm=1,
                    rate_actual_m3_hour=[1, 2, 3],
                    polytropic_head_joule_per_kg=[4, 5, 6],
                    efficiency_fraction=[0.7, 0.8, 0.9],
                ),
                dto.ChartCurve(
                    speed_rpm=1,
                    rate_actual_m3_hour=[4, 5, 6],
                    polytropic_head_joule_per_kg=[7, 8, 9],
                    efficiency_fraction=[0.101, 0.82, 0.9],
                ),
            ],
        )

    def test_invalid_curves(self):
        with pytest.raises(ValidationError) as e:
            dto.VariableSpeedChart(
                curves=[
                    dto.ChartCurve(
                        speed_rpm=1,
                        rate_actual_m3_hour=[4, 5, 6],
                        polytropic_head_joule_per_kg=[7, 8, 9],
                        efficiency_fraction=[101, 0.82, 0.9],
                    )
                ],
            )
        assert e.value.errors()[0]["msg"] == "ensure this value is less than or equal to 1"

        with pytest.raises(ValidationError) as e:
            dto.VariableSpeedChart(
                curves=[
                    dto.ChartCurve(
                        speed_rpm=1,
                        rate_actual_m3_hour="invalid data",
                        polytropic_head_joule_per_kg=[7, 8, 9],
                        efficiency_fraction=[0.7, 0.82, 0.9],
                    )
                ],
            )
        assert e.value.errors()[0]["msg"] == "value is not a valid list"

        with pytest.raises(ValidationError) as e:
            dto.VariableSpeedChart(
                curves=[
                    dto.ChartCurve(
                        speed_rpm=1,
                        rate_actual_m3_hour=[1, 2, "invalid"],
                        polytropic_head_joule_per_kg=[7, 8, 9],
                        efficiency_fraction=[0.7, 0.82, 0.9],
                    )
                ],
            )
        assert e.value.errors()[0]["msg"] == "value is not a valid float"


class TestGenericFromDesignPointCompressorChart:
    def test_create_object(self):
        dto.GenericChartFromDesignPoint(
            polytropic_efficiency_fraction=0.8,
            design_rate_actual_m3_per_hour=7500.0,
            design_polytropic_head_J_per_kg=55000,
        )

    def test_invalid_polytropic_efficiency(self):
        with pytest.raises(ValidationError) as e:
            dto.GenericChartFromDesignPoint(
                polytropic_efficiency_fraction=1.8,
                design_rate_actual_m3_per_hour=7500.0,
                design_polytropic_head_J_per_kg=55000,
            )
        assert e.value.errors()[0]["msg"] == "ensure this value is less than or equal to 1"

    def test_invalid_design_rate(self):
        with pytest.raises(ValidationError) as e:
            dto.GenericChartFromDesignPoint(
                polytropic_efficiency_fraction=0.8,
                design_rate_actual_m3_per_hour="invalid_design_rate",
                design_polytropic_head_J_per_kg=55000,
            )
        assert e.value.errors()[0]["msg"] == "value is not a valid float"


class TestGenericFromInputCompressorChart:
    def test_create_object(self):
        dto.GenericChartFromInput(polytropic_efficiency_fraction=0.8)

    def test_invalid(self):
        with pytest.raises(ValidationError) as e:
            dto.GenericChartFromInput(polytropic_efficiency_fraction="str")
        assert e.value.errors()[0]["msg"] == "value is not a valid float"


class TestCompressorSystemEnergyUsageModel:
    def test_create_system_with_unknown_stages_generic_chart(self):
        compressor_model_generic_chart_unknown_stages = dto.CompressorTrainSimplifiedWithUnknownStages(
            fluid_model=dto.FluidModel(eos_model=dto.types.EoSModel.PR, composition=dto.FluidComposition(methane=1)),
            stage=dto.CompressorStage(
                compressor_chart=dto.GenericChartFromInput(polytropic_efficiency_fraction=0.8),
                inlet_temperature_kelvin=300,
                pressure_drop_before_stage=0,
                remove_liquid_after_cooling=True,
                control_margin=0.0,
            ),
            energy_usage_adjustment_factor=1,
            energy_usage_adjustment_constant=0,
            maximum_pressure_ratio_per_stage=3,
        )

        dto.CompressorSystemConsumerFunction(
            compressors=[
                dto.CompressorSystemCompressor(
                    name="test", compressor_train=compressor_model_generic_chart_unknown_stages
                )
            ],
            operational_settings=[],
            energy_usage_type=dto.types.EnergyUsageType.POWER,
        )


class TestCompressorTrainSimplified:
    def test_valid_train_unknown_stages(self):
        """Testing that the "unknown stages" takes a "stage" argument, and not "stages"."""
        dto.CompressorTrainSimplifiedWithUnknownStages(
            fluid_model=dto.FluidModel(eos_model=dto.types.EoSModel.PR, composition=dto.FluidComposition(methane=1)),
            stage=dto.CompressorStage(
                compressor_chart=dto.GenericChartFromInput(polytropic_efficiency_fraction=0.8),
                inlet_temperature_kelvin=300,
                pressure_drop_before_stage=0,
                remove_liquid_after_cooling=True,
                control_margin=0.0,
            ),
            energy_usage_adjustment_factor=1,
            energy_usage_adjustment_constant=0,
            maximum_pressure_ratio_per_stage=3,
        )

    def test_valid_train_known_stages(self):
        """Testing different chart types that are valid."""
        dto.CompressorTrainSimplifiedWithKnownStages(
            fluid_model=dto.FluidModel(eos_model=dto.types.EoSModel.PR, composition=dto.FluidComposition(methane=1)),
            stages=[
                dto.CompressorStage(
                    compressor_chart=dto.GenericChartFromInput(polytropic_efficiency_fraction=1),
                    inlet_temperature_kelvin=300,
                    pressure_drop_before_stage=0,
                    remove_liquid_after_cooling=True,
                    control_margin=0.0,
                ),
                dto.CompressorStage(
                    compressor_chart=dto.GenericChartFromDesignPoint(
                        polytropic_efficiency_fraction=1,
                        design_polytropic_head_J_per_kg=1,
                        design_rate_actual_m3_per_hour=1,
                    ),
                    inlet_temperature_kelvin=300,
                    pressure_drop_before_stage=0,
                    remove_liquid_after_cooling=True,
                    control_margin=0.0,
                ),
                dto.CompressorStage(
                    compressor_chart=dto.VariableSpeedChart(curves=[]),
                    inlet_temperature_kelvin=300,
                    pressure_drop_before_stage=0,
                    remove_liquid_after_cooling=True,
                    control_margin=0.0,
                ),
            ],
            energy_usage_adjustment_factor=1,
            energy_usage_adjustment_constant=0,
        )

    def test_invalid_chart(self):
        """Simplified does not support single speed charts."""
        with pytest.raises(ValidationError):
            dto.CompressorTrainSimplifiedWithKnownStages(
                fluid_model=dto.FluidModel(
                    eos_model=dto.types.EoSModel.PR, composition=dto.FluidComposition(methane=1)
                ),
                stages=[
                    dto.CompressorStage(
                        compressor_chart=dto.SingleSpeedChart(
                            speed_rpm=1,
                            rate_actual_m3_hour=[],
                            polytropic_head_joule_per_kg=[],
                            efficiency_fraction=[],
                        ),
                        inlet_temperature_kelvin=300,
                        pressure_drop_before_stage=0,
                        remove_liquid_after_cooling=True,
                        control_margin=0.0,
                    )
                ],
                energy_usage_adjustment_factor=1,
                energy_usage_adjustment_constant=0,
            )


class TestSingleSpeedCompressorTrain:
    def test_valid_train_known_stages(self):
        """Testing different chart types that are valid."""
        dto.SingleSpeedCompressorTrain(
            fluid_model=dto.FluidModel(eos_model=dto.types.EoSModel.PR, composition=dto.FluidComposition(methane=1)),
            stages=[
                dto.CompressorStage(
                    compressor_chart=dto.SingleSpeedChart(
                        speed_rpm=1,
                        rate_actual_m3_hour=[1, 2],
                        polytropic_head_joule_per_kg=[3, 4],
                        efficiency_fraction=[0.5, 0.5],
                    ),
                    inlet_temperature_kelvin=300,
                    pressure_drop_before_stage=0,
                    remove_liquid_after_cooling=True,
                    control_margin=0.0,
                )
            ],
            energy_usage_adjustment_factor=1,
            energy_usage_adjustment_constant=0,
            pressure_control=dto.types.FixedSpeedPressureControl.DOWNSTREAM_CHOKE,
        )

    def test_invalid_chart(self):
        """Single speed does not support variable speed charts."""
        with pytest.raises(ValidationError):
            dto.SingleSpeedCompressorTrain(
                fluid_model=dto.FluidModel(
                    eos_model=dto.types.EoSModel.PR, composition=dto.FluidComposition(methane=1)
                ),
                stages=[
                    dto.CompressorStage(
                        compressor_chart=dto.VariableSpeedChart(curves=[]),
                        inlet_temperature_kelvin=300,
                        pressure_drop_before_stage=0,
                        remove_liquid_after_cooling=True,
                        control_margin=0.0,
                    )
                ],
                energy_usage_adjustment_factor=1,
                energy_usage_adjustment_constant=0,
                pressure_control=dto.types.FixedSpeedPressureControl.DOWNSTREAM_CHOKE,
            )


class TestVariableSpeedCompressorTrain:
    def test_compatible_stages(self):
        dto.VariableSpeedCompressorTrain(
            fluid_model=dto.FluidModel(eos_model=dto.types.EoSModel.PR, composition=dto.FluidComposition(methane=1)),
            stages=[
                dto.CompressorStage(
                    compressor_chart=dto.VariableSpeedChart(
                        curves=[
                            dto.ChartCurve(
                                speed_rpm=1,
                                rate_actual_m3_hour=[1, 2, 3],
                                polytropic_head_joule_per_kg=[1, 2, 3],
                                efficiency_fraction=[0.1, 0.2, 0.3],
                            )
                        ],
                    ),
                    inlet_temperature_kelvin=300,
                    pressure_drop_before_stage=0,
                    remove_liquid_after_cooling=True,
                    control_margin=0.0,
                ),
                dto.CompressorStage(
                    compressor_chart=dto.VariableSpeedChart(
                        curves=[
                            dto.ChartCurve(
                                speed_rpm=1,
                                rate_actual_m3_hour=[1, 2, 3],
                                polytropic_head_joule_per_kg=[1, 2, 3],
                                efficiency_fraction=[0.1, 0.2, 0.3],
                            ),
                            dto.ChartCurve(
                                speed_rpm=2,
                                rate_actual_m3_hour=[1, 2, 3],
                                polytropic_head_joule_per_kg=[1, 2, 3],
                                efficiency_fraction=[0.1, 0.2, 0.3],
                            ),
                        ],
                    ),
                    inlet_temperature_kelvin=300,
                    pressure_drop_before_stage=0,
                    remove_liquid_after_cooling=False,
                    control_margin=0.0,
                ),
            ],
            energy_usage_adjustment_factor=1,
            energy_usage_adjustment_constant=0,
            pressure_control=dto.types.FixedSpeedPressureControl.DOWNSTREAM_CHOKE,
        )

    def test_incompatible_stages(self):
        with pytest.raises(
            ValidationError,
            match=r".*Variable speed compressors in compressor train have incompatible compressor charts.*",
        ):
            dto.VariableSpeedCompressorTrain(
                fluid_model=dto.FluidModel(
                    eos_model=dto.types.EoSModel.PR, composition=dto.FluidComposition(methane=1)
                ),
                stages=[
                    dto.CompressorStage(
                        compressor_chart=dto.VariableSpeedChart(
                            curves=[
                                dto.ChartCurve(
                                    speed_rpm=3,
                                    rate_actual_m3_hour=[1, 2, 3],
                                    polytropic_head_joule_per_kg=[1, 2, 3],
                                    efficiency_fraction=[0.1, 0.2, 0.3],
                                )
                            ],
                        ),
                        inlet_temperature_kelvin=300,
                        pressure_drop_before_stage=0,
                        remove_liquid_after_cooling=True,
                        control_margin=0.0,
                    ),
                    dto.CompressorStage(
                        compressor_chart=dto.VariableSpeedChart(
                            curves=[
                                dto.ChartCurve(
                                    speed_rpm=1,
                                    rate_actual_m3_hour=[1, 2, 3],
                                    polytropic_head_joule_per_kg=[1, 2, 3],
                                    efficiency_fraction=[0.1, 0.2, 0.3],
                                ),
                                dto.ChartCurve(
                                    speed_rpm=2,
                                    rate_actual_m3_hour=[1, 2, 3],
                                    polytropic_head_joule_per_kg=[1, 2, 3],
                                    efficiency_fraction=[0.1, 0.2, 0.3],
                                ),
                            ],
                        ),
                        inlet_temperature_kelvin=300,
                        pressure_drop_before_stage=0,
                        remove_liquid_after_cooling=False,
                        control_margin=0.0,
                    ),
                ],
                energy_usage_adjustment_factor=1,
                energy_usage_adjustment_constant=0,
                pressure_control=dto.types.FixedSpeedPressureControl.DOWNSTREAM_CHOKE,
            )
