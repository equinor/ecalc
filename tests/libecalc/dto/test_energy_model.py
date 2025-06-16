import pytest
from pydantic import ValidationError

import libecalc.common.energy_usage_type
import libecalc.common.fixed_speed_pressure_control
import libecalc.common.fluid
from libecalc.common.fluid import FluidModel
from libecalc.common.serializable_chart import ChartCurveDTO, SingleSpeedChartDTO, VariableSpeedChartDTO
from libecalc.common.time_utils import Frequency
from libecalc.domain.component_validation_error import (
    ProcessChartTypeValidationException,
    ProcessChartValueValidationException,
    ProcessEqualLengthValidationException,
)
from libecalc.domain.process.compressor import dto
from libecalc.domain.process.dto.consumer_system import CompressorSystemCompressor, CompressorSystemConsumerFunction
from libecalc.domain.process.dto.turbine import Turbine
from libecalc.domain.process.value_objects.chart.generic import GenericChartFromDesignPoint, GenericChartFromInput
from libecalc.domain.process.value_objects.fluid_stream.fluid_composition import FluidComposition
from libecalc.presentation.yaml.model import YamlModel
from libecalc.presentation.yaml.model_validation_exception import ModelValidationException
from libecalc.testing.yaml_builder import YamlTurbineBuilder


class TestTurbine:
    def test_turbine(self):
        Turbine(
            lower_heating_value=38,
            turbine_loads=[0, 2.352, 4.589, 6.853, 9.125, 11.399, 13.673, 15.947, 18.223, 20.496, 22.767],
            turbine_efficiency_fractions=[0, 0.138, 0.21, 0.255, 0.286, 0.31, 0.328, 0.342, 0.353, 0.36, 0.362],
            energy_usage_adjustment_constant=0,
            energy_usage_adjustment_factor=0,
        )

    def test_unequal_load_and_efficiency_lengths(self):
        with pytest.raises(ProcessEqualLengthValidationException) as e:
            Turbine(
                lower_heating_value=38,
                turbine_loads=[0, 2.352, 4.589, 6.853, 9.125, 11.399, 13.673, 15.947, 18.223, 20.496],
                turbine_efficiency_fractions=[0, 0.138, 0.21, 0.255, 0.286, 0.31, 0.328, 0.342, 0.353, 0.36, 0.362],
                energy_usage_adjustment_constant=0,
                energy_usage_adjustment_factor=1.0,
            )
        assert "Need equal number of load and efficiency values for turbine model" in str(e.value)

    def test_invalid_efficiency_fractions(
        self,
        yaml_asset_configuration_service_factory,
        yaml_asset_builder_factory,
        resource_service_factory,
    ):
        """
        Test to validate that the turbine efficiency fractions are within the valid range (0 to 1).

        This test ensures that:
        1. Invalid efficiency fractions (values below 0 or above 1) are correctly identified.
        2. The appropriate exception (ModelValidationException) is raised.
        3. The error message contains the correct details about the invalid values.

        """

        yaml_turbine = (
            YamlTurbineBuilder()
            .with_test_data()
            .with_turbine_efficiencies([0, 0.138, 0.21, 5.0, 0.286, 0.31, -0.328, 0.342, 0.353, 0.354, 0.36])
        )
        asset = yaml_asset_builder_factory().with_test_data().with_models([yaml_turbine.validate()]).validate()

        yaml_asset = YamlModel(
            configuration=yaml_asset_configuration_service_factory(asset, "asset").get_configuration(),
            resource_service=resource_service_factory({}),
            output_frequency=Frequency.YEAR,
        )
        with pytest.raises(ModelValidationException) as e:
            yaml_asset.validate_for_run()

        assert "Turbine efficiency fraction should be a number between 0 and 1. Invalid values: [5.0, -0.328]" in str(
            e.value
        )


class TestVariableSpeedCompressorChart:
    def test_variable_speed_compressor_chart(self):
        VariableSpeedChartDTO(
            curves=[
                ChartCurveDTO(
                    speed_rpm=1,
                    rate_actual_m3_hour=[1, 2, 3],
                    polytropic_head_joule_per_kg=[4, 5, 6],
                    efficiency_fraction=[0.7, 0.8, 0.9],
                ),
                ChartCurveDTO(
                    speed_rpm=1,
                    rate_actual_m3_hour=[4, 5, 6],
                    polytropic_head_joule_per_kg=[7, 8, 9],
                    efficiency_fraction=[0.101, 0.82, 0.9],
                ),
            ],
        )

    def test_invalid_curves(self):
        with pytest.raises(ValidationError) as e:
            VariableSpeedChartDTO(
                curves=[
                    ChartCurveDTO(
                        speed_rpm=1,
                        rate_actual_m3_hour=[4, 5, 6],
                        polytropic_head_joule_per_kg=[7, 8, 9],
                        efficiency_fraction=[101, 0.82, 0.9],
                    )
                ],
            )
        assert "Input should be less than or equal to 1" in str(e.value)

        with pytest.raises(ValidationError) as e:
            VariableSpeedChartDTO(
                curves=[
                    ChartCurveDTO(
                        speed_rpm=1,
                        rate_actual_m3_hour="invalid data",
                        polytropic_head_joule_per_kg=[7, 8, 9],
                        efficiency_fraction=[0.7, 0.82, 0.9],
                    )
                ],
            )
        assert "Input should be a valid list" in str(e.value)

        with pytest.raises(ValidationError) as e:
            VariableSpeedChartDTO(
                curves=[
                    ChartCurveDTO(
                        speed_rpm=1,
                        rate_actual_m3_hour=[1, 2, "invalid"],
                        polytropic_head_joule_per_kg=[7, 8, 9],
                        efficiency_fraction=[0.7, 0.82, 0.9],
                    )
                ],
            )
        assert "Input should be a valid number, unable to parse string as a number" in str(e.value)


class TestGenericFromDesignPointCompressorChart:
    def test_create_object(self):
        GenericChartFromDesignPoint(
            polytropic_efficiency_fraction=0.8,
            design_rate_actual_m3_per_hour=7500.0,
            design_polytropic_head_J_per_kg=55000,
        )

    def test_invalid_polytropic_efficiency(self):
        with pytest.raises(ProcessChartValueValidationException) as e:
            GenericChartFromDesignPoint(
                polytropic_efficiency_fraction=1.8,
                design_rate_actual_m3_per_hour=7500.0,
                design_polytropic_head_J_per_kg=55000,
            )
        assert "polytropic_efficiency_fraction must be greater than 0 and less than or equal to 1" in str(e.value)

    def test_invalid_design_rate(self):
        with pytest.raises(ProcessChartValueValidationException) as e:
            GenericChartFromDesignPoint(
                polytropic_efficiency_fraction=0.8,
                design_rate_actual_m3_per_hour="invalid_design_rate",
                design_polytropic_head_J_per_kg=55000,
            )
        assert "design_rate_actual_m3_per_hour must be a number" in str(e.value)


class TestGenericFromInputCompressorChart:
    def test_create_object(self):
        GenericChartFromInput(polytropic_efficiency_fraction=0.8)

    def test_invalid(self):
        with pytest.raises(ProcessChartValueValidationException) as e:
            GenericChartFromInput(polytropic_efficiency_fraction="str")
        assert "polytropic_efficiency_fraction must be a number" in str(e.value)


class TestCompressorSystemEnergyUsageModel:
    def test_create_system_with_unknown_stages_generic_chart(self):
        compressor_model_generic_chart_unknown_stages = dto.CompressorTrainSimplifiedWithUnknownStages(
            fluid_model=FluidModel(
                eos_model=libecalc.common.fluid.EoSModel.PR, composition=FluidComposition(methane=1)
            ),
            stage=dto.CompressorStage(
                compressor_chart=GenericChartFromInput(polytropic_efficiency_fraction=0.8),
                inlet_temperature_kelvin=300,
                pressure_drop_before_stage=0,
                remove_liquid_after_cooling=True,
                control_margin=0.0,
            ),
            energy_usage_adjustment_factor=1,
            energy_usage_adjustment_constant=0,
            maximum_pressure_ratio_per_stage=3,
        )

        CompressorSystemConsumerFunction(
            compressors=[
                CompressorSystemCompressor(name="test", compressor_train=compressor_model_generic_chart_unknown_stages)
            ],
            operational_settings=[],
            energy_usage_type=libecalc.common.energy_usage_type.EnergyUsageType.POWER,
        )


class TestCompressorTrainSimplified:
    def test_valid_train_unknown_stages(self):
        """Testing that the "unknown stages" takes a "stage" argument, and not "stages"."""
        dto.CompressorTrainSimplifiedWithUnknownStages(
            fluid_model=FluidModel(
                eos_model=libecalc.common.fluid.EoSModel.PR, composition=FluidComposition(methane=1)
            ),
            stage=dto.CompressorStage(
                compressor_chart=GenericChartFromInput(polytropic_efficiency_fraction=0.8),
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
            fluid_model=FluidModel(
                eos_model=libecalc.common.fluid.EoSModel.PR, composition=FluidComposition(methane=1)
            ),
            stages=[
                dto.CompressorStage(
                    compressor_chart=GenericChartFromInput(polytropic_efficiency_fraction=1),
                    inlet_temperature_kelvin=300,
                    pressure_drop_before_stage=0,
                    remove_liquid_after_cooling=True,
                    control_margin=0.0,
                ),
                dto.CompressorStage(
                    compressor_chart=GenericChartFromDesignPoint(
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
                    compressor_chart=VariableSpeedChartDTO(curves=[]),
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
                fluid_model=FluidModel(
                    eos_model=libecalc.common.fluid.EoSModel.PR,
                    composition=FluidComposition(methane=1),
                ),
                stages=[
                    dto.CompressorStage(
                        compressor_chart=SingleSpeedChartDTO(
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
            fluid_model=FluidModel(
                eos_model=libecalc.common.fluid.EoSModel.PR, composition=FluidComposition(methane=1)
            ),
            stages=[
                dto.CompressorStage(
                    compressor_chart=SingleSpeedChartDTO(
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
            pressure_control=libecalc.common.fixed_speed_pressure_control.FixedSpeedPressureControl.DOWNSTREAM_CHOKE,
        )

    def test_invalid_chart(self):
        """Single speed does not support variable speed charts."""
        with pytest.raises(ProcessChartTypeValidationException):
            dto.SingleSpeedCompressorTrain(
                fluid_model=FluidModel(
                    eos_model=libecalc.common.fluid.EoSModel.PR,
                    composition=FluidComposition(methane=1),
                ),
                stages=[
                    dto.CompressorStage(
                        compressor_chart=VariableSpeedChartDTO(curves=[]),
                        inlet_temperature_kelvin=300,
                        pressure_drop_before_stage=0,
                        remove_liquid_after_cooling=True,
                        control_margin=0.0,
                    )
                ],
                energy_usage_adjustment_factor=1,
                energy_usage_adjustment_constant=0,
                pressure_control=libecalc.common.fixed_speed_pressure_control.FixedSpeedPressureControl.DOWNSTREAM_CHOKE,
            )


class TestVariableSpeedCompressorTrain:
    def test_compatible_stages(self):
        dto.VariableSpeedCompressorTrain(
            fluid_model=FluidModel(
                eos_model=libecalc.common.fluid.EoSModel.PR, composition=FluidComposition(methane=1)
            ),
            stages=[
                dto.CompressorStage(
                    compressor_chart=VariableSpeedChartDTO(
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
                    pressure_drop_before_stage=0,
                    remove_liquid_after_cooling=True,
                    control_margin=0.0,
                ),
                dto.CompressorStage(
                    compressor_chart=VariableSpeedChartDTO(
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
                    pressure_drop_before_stage=0,
                    remove_liquid_after_cooling=False,
                    control_margin=0.0,
                ),
            ],
            energy_usage_adjustment_factor=1,
            energy_usage_adjustment_constant=0,
            pressure_control=libecalc.common.fixed_speed_pressure_control.FixedSpeedPressureControl.DOWNSTREAM_CHOKE,
        )

    def test_incompatible_stages(self):
        with pytest.raises(ProcessChartTypeValidationException) as e:
            dto.VariableSpeedCompressorTrain(
                fluid_model=FluidModel(
                    eos_model=libecalc.common.fluid.EoSModel.PR,
                    composition=FluidComposition(methane=1),
                ),
                stages=[
                    dto.CompressorStage(
                        compressor_chart=VariableSpeedChartDTO(
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
                        pressure_drop_before_stage=0,
                        remove_liquid_after_cooling=True,
                        control_margin=0.0,
                    ),
                    dto.CompressorStage(
                        compressor_chart=VariableSpeedChartDTO(
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
                        pressure_drop_before_stage=0,
                        remove_liquid_after_cooling=False,
                        control_margin=0.0,
                    ),
                ],
                energy_usage_adjustment_factor=1,
                energy_usage_adjustment_constant=0,
                pressure_control=libecalc.common.fixed_speed_pressure_control.FixedSpeedPressureControl.DOWNSTREAM_CHOKE,
            )

        assert "Variable speed compressors in compressor train have incompatible compressor charts" in str(
            e.value.errors()
        )
