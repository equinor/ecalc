from typing import Literal

from libecalc.common.energy_model_type import EnergyModelType
from libecalc.common.fixed_speed_pressure_control import FixedSpeedPressureControl
from libecalc.common.fluid import (
    FluidModel,
    MultipleStreamsAndPressureStream,
)
from libecalc.common.serializable_chart import SingleSpeedChartDTO, VariableSpeedChartDTO
from libecalc.domain.component_validation_error import (
    ModelValidationError,
    ProcessChartTypeValidationException,
    ProcessDischargePressureValidationException,
    ProcessPressureRatioValidationException,
)
from libecalc.domain.process.compressor.dto.stage import (
    CompressorStage,
)
from libecalc.domain.process.dto.base import EnergyModel
from libecalc.presentation.yaml.validation_errors import Location


class CompressorTrain(EnergyModel):
    typ: EnergyModelType

    def __init__(
        self,
        energy_usage_adjustment_constant: float,
        energy_usage_adjustment_factor: float,
        typ: EnergyModelType,
        stages: list[CompressorStage],
        fluid_model: FluidModel | None = None,
        pressure_control: FixedSpeedPressureControl | None = None,
        calculate_max_rate: bool = False,
        maximum_power: float | None = None,
    ):
        super().__init__(energy_usage_adjustment_constant, energy_usage_adjustment_factor)
        self.typ = typ
        self.stages = stages
        self.fluid_model = fluid_model
        self.calculate_max_rate = calculate_max_rate
        self.maximum_power = maximum_power
        self.pressure_control = pressure_control


class CompressorTrainSimplifiedWithKnownStages(CompressorTrain):
    typ: Literal[EnergyModelType.COMPRESSOR_TRAIN_SIMPLIFIED_WITH_KNOWN_STAGES] = (
        EnergyModelType.COMPRESSOR_TRAIN_SIMPLIFIED_WITH_KNOWN_STAGES
    )

    # Not in use:
    pressure_control: FixedSpeedPressureControl | None = None  # Not relevant for simplified trains.

    def __init__(
        self,
        energy_usage_adjustment_constant: float,
        energy_usage_adjustment_factor: float,
        stages: list[CompressorStage],
        fluid_model: FluidModel,
        calculate_max_rate: bool = False,
        maximum_power: float | None = None,
    ):
        super().__init__(
            energy_usage_adjustment_constant=energy_usage_adjustment_constant,
            energy_usage_adjustment_factor=energy_usage_adjustment_factor,
            typ=self.typ,
            stages=stages,
            fluid_model=fluid_model,
            pressure_control=self.pressure_control,
            calculate_max_rate=calculate_max_rate,
            maximum_power=maximum_power,
        )

    def _validate_stages(self, stages):
        for stage in stages:
            if isinstance(stage.compressor_chart, SingleSpeedChartDTO):
                msg = "Simplified Compressor Train does not support Single Speed Compressor Chart."
                f" Given type was {type(stage.compressor_chart)}"

                raise ProcessChartTypeValidationException(
                    errors=[
                        ModelValidationError(name=self.typ.value, location=Location([self.typ.value]), message=str(msg))
                    ],
                )
        return stages


class CompressorTrainSimplifiedWithUnknownStages(CompressorTrain):
    """Unknown stages does not have stages, instead we have one stage that will be multiplied as many times as needed.
    Will be constrained by a maximum pressure ratio per stage.
    """

    typ: Literal[EnergyModelType.COMPRESSOR_TRAIN_SIMPLIFIED_WITH_UNKNOWN_STAGES] = (
        EnergyModelType.COMPRESSOR_TRAIN_SIMPLIFIED_WITH_UNKNOWN_STAGES
    )

    # Not in use:
    stages: list[CompressorStage] = []  # Not relevant since the stage is Unknown
    pressure_control: FixedSpeedPressureControl | None = None  # Not relevant for simplified trains.

    def __init__(
        self,
        energy_usage_adjustment_constant: float,
        energy_usage_adjustment_factor: float,
        fluid_model: FluidModel,
        stage: CompressorStage,
        maximum_pressure_ratio_per_stage: float,
        calculate_max_rate: bool = False,
        maximum_power: float | None = None,
    ):
        super().__init__(
            energy_usage_adjustment_constant,
            energy_usage_adjustment_factor,
            self.typ,
            stages=self.stages,
            fluid_model=fluid_model,
            pressure_control=self.pressure_control,
            calculate_max_rate=calculate_max_rate,
            maximum_power=maximum_power,
        )
        self.stage = stage
        self.maximum_pressure_ratio_per_stage = maximum_pressure_ratio_per_stage
        self.fluid_model = fluid_model
        self._validate_maximum_pressure_ratio_per_stage()

    def _validate_maximum_pressure_ratio_per_stage(self):
        if self.maximum_pressure_ratio_per_stage < 0:
            msg = f"maximum_pressure_ratio_per_stage must be greater than or equal to 0. Invalid value: {self.maximum_pressure_ratio_per_stage}"

            raise ProcessPressureRatioValidationException(
                errors=[
                    ModelValidationError(name=self.typ.value, location=Location([self.typ.value]), message=str(msg))
                ],
            )


class SingleSpeedCompressorTrain(CompressorTrain):
    """Single speed train has a control mechanism for max discharge pressure."""

    typ: Literal[EnergyModelType.SINGLE_SPEED_COMPRESSOR_TRAIN_COMMON_SHAFT] = (
        EnergyModelType.SINGLE_SPEED_COMPRESSOR_TRAIN_COMMON_SHAFT
    )

    def __init__(
        self,
        energy_usage_adjustment_constant: float,
        energy_usage_adjustment_factor: float,
        stages: list[CompressorStage],
        fluid_model: FluidModel | None = None,
        pressure_control: FixedSpeedPressureControl | None = None,
        calculate_max_rate: bool = False,
        maximum_power: float | None = None,
        maximum_discharge_pressure: float | None = None,
    ):
        super().__init__(
            energy_usage_adjustment_constant=energy_usage_adjustment_constant,
            energy_usage_adjustment_factor=energy_usage_adjustment_factor,
            typ=self.typ,
            stages=stages,
            fluid_model=fluid_model,
            pressure_control=pressure_control,
            calculate_max_rate=calculate_max_rate,
            maximum_power=maximum_power,
        )
        self.maximum_discharge_pressure = maximum_discharge_pressure
        self._validate_maximum_discharge_pressure()
        self._validate_stages(stages)

    def _validate_maximum_discharge_pressure(self):
        if self.maximum_discharge_pressure is not None and self.maximum_discharge_pressure < 0:
            msg = f"maximum_discharge_pressure must be greater than or equal to 0. Invalid value: {self.maximum_discharge_pressure}"

            raise ProcessDischargePressureValidationException(
                errors=[
                    ModelValidationError(name=self.typ.value, location=Location([self.typ.value]), message=str(msg))
                ],
            )

    def _validate_stages(self, stages):
        for stage in stages:
            if not isinstance(stage.compressor_chart, SingleSpeedChartDTO):
                msg = "Single Speed Compressor train only accepts Single Speed Compressor Charts."
                f" Given type was {type(stage.compressor_chart)}"

                raise ProcessChartTypeValidationException(
                    errors=[
                        ModelValidationError(name=self.typ.value, location=Location([self.typ.value]), message=str(msg))
                    ],
                )


class VariableSpeedCompressorTrain(CompressorTrain):
    typ: Literal[EnergyModelType.VARIABLE_SPEED_COMPRESSOR_TRAIN_COMMON_SHAFT] = (
        EnergyModelType.VARIABLE_SPEED_COMPRESSOR_TRAIN_COMMON_SHAFT
    )

    def __init__(
        self,
        energy_usage_adjustment_constant: float,
        energy_usage_adjustment_factor: float,
        stages: list[CompressorStage],
        fluid_model: FluidModel | None = None,
        pressure_control: FixedSpeedPressureControl | None = None,
        calculate_max_rate: bool = False,
        maximum_power: float | None = None,
    ):
        super().__init__(
            energy_usage_adjustment_constant=energy_usage_adjustment_constant,
            energy_usage_adjustment_factor=energy_usage_adjustment_factor,
            typ=self.typ,
            stages=stages,
            fluid_model=fluid_model,
            pressure_control=pressure_control,
            calculate_max_rate=calculate_max_rate,
            maximum_power=maximum_power,
        )
        self._validate_stages(stages)

    def _validate_stages(self, stages):
        min_speed_per_stage = []
        max_speed_per_stage = []
        for stage in stages:
            if not isinstance(stage.compressor_chart, VariableSpeedChartDTO):
                msg = "Variable Speed Compressor train only accepts Variable Speed Compressor Charts."
                f" Given type was {type(stage.compressor_chart)}"

                raise ProcessChartTypeValidationException(
                    errors=[
                        ModelValidationError(name=self.typ.value, location=Location([self.typ.value]), message=str(msg))
                    ],
                )

            max_speed_per_stage.append(stage.compressor_chart.max_speed)
            min_speed_per_stage.append(stage.compressor_chart.min_speed)
        if max(min_speed_per_stage) > min(max_speed_per_stage):
            msg = "Variable speed compressors in compressor train have incompatible compressor charts."
            f" Stage {min_speed_per_stage.index(max(min_speed_per_stage)) + 1}'s minimum speed is higher"
            f" than max speed of stage {max_speed_per_stage.index(min(max_speed_per_stage)) + 1}"

            raise ProcessChartTypeValidationException(
                errors=[
                    ModelValidationError(name=self.typ.value, location=Location([self.typ.value]), message=str(msg))
                ],
            )


class VariableSpeedCompressorTrainMultipleStreamsAndPressures(CompressorTrain):
    """This is the dto for the "advanced" (common shaft) compressor train model, with multiple input and output streams and
    possibly an interstage control pressure
    The streams are listed separately and then mapped into the stages. We need to keep the info of the input ordering of
    the streams, as this determine the mapping of which rate is mapped to which stream at evaluation
    Two options - either keep the streams as a separate attribute from stages and do the mapping at evaluation, or do
    the mapping of streams and add these to the stages now, but let the stream get a number representing it's placement
    in the syntax. The first option - keep the reference and do the mapping later is used here to keep the yaml syntax
    and the dto similar.
    """

    typ: Literal[EnergyModelType.VARIABLE_SPEED_COMPRESSOR_TRAIN_MULTIPLE_STREAMS_AND_PRESSURES] = (
        EnergyModelType.VARIABLE_SPEED_COMPRESSOR_TRAIN_MULTIPLE_STREAMS_AND_PRESSURES
    )
    streams: list[MultipleStreamsAndPressureStream]
    stages: list[CompressorStage]

    # Not in use:
    fluid_model: FluidModel | None = None  # Not relevant. set by the individual stream.

    def __init__(
        self,
        energy_usage_adjustment_constant: float,
        energy_usage_adjustment_factor: float,
        streams: list[MultipleStreamsAndPressureStream],
        stages: list[CompressorStage],
        calculate_max_rate: bool = False,
        maximum_power: float | None = None,
        pressure_control: FixedSpeedPressureControl | None = None,
    ):
        super().__init__(
            energy_usage_adjustment_constant,
            energy_usage_adjustment_factor,
            self.typ,
            stages,
            fluid_model=self.fluid_model,
            pressure_control=None,
            calculate_max_rate=calculate_max_rate,
            maximum_power=maximum_power,
        )
        self.streams = streams
        self.stages = stages
        if pressure_control and not isinstance(pressure_control, FixedSpeedPressureControl):
            raise TypeError(f"pressure_control must be of type FixedSpeedPressureControl, got {type(pressure_control)}")
        self.pressure_control = pressure_control
        self._validate_stages(stages)

    def _validate_stages(self, stages):
        if sum([stage.has_control_pressure for stage in stages]) > 1:
            raise ValueError("Only one interstage pressure should be defined for a compressor train")
        min_speed_per_stage = []
        max_speed_per_stage = []
        for stage in stages:
            if not isinstance(stage.compressor_chart, VariableSpeedChartDTO):
                msg = "Variable Speed Compressor train only accepts Variable Speed Compressor Charts."
                f" Given type was {type(stage.compressor_chart)}"

                raise ProcessChartTypeValidationException(
                    errors=[
                        ModelValidationError(name=self.typ.value, location=Location([self.typ.value]), message=str(msg))
                    ],
                )
            max_speed_per_stage.append(stage.compressor_chart.max_speed)
            min_speed_per_stage.append(stage.compressor_chart.min_speed)
        if max(min_speed_per_stage) > min(max_speed_per_stage):
            msg = "Variable speed compressors in compressor train have incompatible compressor charts."
            f" Stage {min_speed_per_stage.index(max(min_speed_per_stage)) + 1}'s minimum speed is higher"
            f" than max speed of stage {max_speed_per_stage.index(min(max_speed_per_stage)) + 1}"

            raise ProcessChartTypeValidationException(
                errors=[
                    ModelValidationError(name=self.typ.value, location=Location([self.typ.value]), message=str(msg))
                ],
            )

    @property
    def has_interstage_pressure(self):
        return any(stage.has_control_pressure for stage in self.stages)

    @property
    def stage_number_interstage_pressure(self):
        """Number of the stage after the fixed intermediate pressure, meaning the intermediate pressure will be the
        inlet pressure of this stage. Must be larger than 0 and smaller than the number of stages in the train
        (zero indexed, first stage is stage_0).
        """
        return (
            [i for i, stage in enumerate(self.stages) if stage.has_control_pressure][0]
            if self.has_interstage_pressure
            else None
        )

    @property
    def stream_references(self):
        return {
            stream_ref: i
            for i, stage in enumerate(self.stages)
            if stage.stream_reference
            for stream_ref in stage.stream_reference
        }

    @property
    def pressure_control_first_part(self) -> FixedSpeedPressureControl:
        return (
            self.stages[self.stage_number_interstage_pressure].interstage_pressure_control.upstream_pressure_control
            if self.stage_number_interstage_pressure
            else None
        )

    @property
    def pressure_control_last_part(self) -> FixedSpeedPressureControl:
        return (
            self.stages[self.stage_number_interstage_pressure].interstage_pressure_control.downstream_pressure_control
            if self.stage_number_interstage_pressure
            else None
        )
