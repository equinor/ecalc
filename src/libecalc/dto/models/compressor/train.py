from typing import List, Literal, Optional

from pydantic import Field, field_validator
from typing_extensions import Annotated

from libecalc.dto.models.base import EnergyModel
from libecalc.dto.models.compressor.chart import SingleSpeedChart, VariableSpeedChart
from libecalc.dto.models.compressor.fluid import (
    FluidModel,
    MultipleStreamsAndPressureStream,
)
from libecalc.dto.models.compressor.stage import (
    CompressorStage,
    MultipleStreamsCompressorStage,
)
from libecalc.dto.types import EnergyModelType, FixedSpeedPressureControl


class CompressorTrain(EnergyModel):
    typ: EnergyModelType
    stages: List[CompressorStage]
    fluid_model: FluidModel
    calculate_max_rate: bool = False
    maximum_power: Optional[float] = None
    pressure_control: FixedSpeedPressureControl


class CompressorTrainSimplifiedWithKnownStages(CompressorTrain):
    typ: Literal[
        EnergyModelType.COMPRESSOR_TRAIN_SIMPLIFIED_WITH_KNOWN_STAGES
    ] = EnergyModelType.COMPRESSOR_TRAIN_SIMPLIFIED_WITH_KNOWN_STAGES

    # Not in use:
    pressure_control: Optional[FixedSpeedPressureControl] = None  # Not relevant for simplified trains.

    @field_validator("stages")
    @classmethod
    def _validate_stages(cls, stages):
        for stage in stages:
            if isinstance(stage.compressor_chart, SingleSpeedChart):
                raise ValueError(
                    "Simplified Compressor Train does not support Single Speed Compressor Chart."
                    f" Given type was {type(stage.compressor_chart)}"
                )
        return stages


class CompressorTrainSimplifiedWithUnknownStages(CompressorTrain):
    """Unknown stages does not have stages, instead we have one stage that will be multiplied as many times as needed.
    Will be constrained by a maximum pressure ratio per stage.
    """

    typ: Literal[
        EnergyModelType.COMPRESSOR_TRAIN_SIMPLIFIED_WITH_UNKNOWN_STAGES
    ] = EnergyModelType.COMPRESSOR_TRAIN_SIMPLIFIED_WITH_UNKNOWN_STAGES
    stage: CompressorStage
    maximum_pressure_ratio_per_stage: Annotated[float, Field(ge=0)]

    # Not in use:
    stages: List[CompressorStage] = []  # Not relevant since the stage is Unknown
    pressure_control: Optional[FixedSpeedPressureControl] = None  # Not relevant for simplified trains.

    @field_validator("stage")
    @classmethod
    def _validate_stages(cls, stage):
        if isinstance(stage.compressor_chart, SingleSpeedChart):
            raise ValueError(
                "Simplified Compressor Train does not support Single Speed Compressor Chart."
                f" Given type was {type(stage.compressor_chart)}"
            )
        return stage


class SingleSpeedCompressorTrain(CompressorTrain):
    """Single speed train has a control mechanism for max discharge pressure."""

    typ: Literal[
        EnergyModelType.SINGLE_SPEED_COMPRESSOR_TRAIN_COMMON_SHAFT
    ] = EnergyModelType.SINGLE_SPEED_COMPRESSOR_TRAIN_COMMON_SHAFT
    maximum_discharge_pressure: Optional[Annotated[float, Field(ge=0)]] = None

    @field_validator("stages")
    @classmethod
    def _validate_stages(cls, stages):
        for stage in stages:
            if not isinstance(stage.compressor_chart, SingleSpeedChart):
                raise ValueError(
                    "Single Speed Compressor train only accepts Single Speed Compressor Charts."
                    f" Given type was {type(stage.compressor_chart)}"
                )
        return stages


class VariableSpeedCompressorTrain(CompressorTrain):
    typ: Literal[
        EnergyModelType.VARIABLE_SPEED_COMPRESSOR_TRAIN_COMMON_SHAFT
    ] = EnergyModelType.VARIABLE_SPEED_COMPRESSOR_TRAIN_COMMON_SHAFT

    @field_validator("stages")
    @classmethod
    def _validate_stages(cls, stages):
        min_speed_per_stage = []
        max_speed_per_stage = []
        for stage in stages:
            if not isinstance(stage.compressor_chart, VariableSpeedChart):
                raise ValueError(
                    "Variable Speed Compressor train only accepts Variable Speed Compressor Charts."
                    f" Given type was {type(stage.compressor_chart)}"
                )
            max_speed_per_stage.append(stage.compressor_chart.max_speed)
            min_speed_per_stage.append(stage.compressor_chart.min_speed)
        if max(min_speed_per_stage) > min(max_speed_per_stage):
            raise ValueError(
                "Variable speed compressors in compressor train have incompatible compressor charts."
                f" Stage {min_speed_per_stage.index(max(min_speed_per_stage)) + 1}'s minimum speed is higher"
                f" than max speed of stage {max_speed_per_stage.index(min(max_speed_per_stage)) + 1}"
            )
        return stages


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

    typ: Literal[
        EnergyModelType.VARIABLE_SPEED_COMPRESSOR_TRAIN_MULTIPLE_STREAMS_AND_PRESSURES
    ] = EnergyModelType.VARIABLE_SPEED_COMPRESSOR_TRAIN_MULTIPLE_STREAMS_AND_PRESSURES
    streams: List[MultipleStreamsAndPressureStream]
    stages: List[MultipleStreamsCompressorStage]

    # Not in use:
    fluid_model: Optional[FluidModel] = None  # Not relevant. set by the individual stream.

    @field_validator("stages")
    @classmethod
    def _validate_stages(cls, stages):
        if sum([stage.has_control_pressure for stage in stages]) > 1:
            raise ValueError("Only one interstage pressure should be defined for a compressor train")
        min_speed_per_stage = []
        max_speed_per_stage = []
        for stage in stages:
            if not isinstance(stage.compressor_chart, VariableSpeedChart):
                raise ValueError(
                    "Variable Speed Compressor train only accepts Variable Speed Compressor Charts."
                    f" Given type was {type(stage.compressor_chart)}"
                )
            max_speed_per_stage.append(stage.compressor_chart.max_speed)
            min_speed_per_stage.append(stage.compressor_chart.min_speed)
        if max(min_speed_per_stage) > min(max_speed_per_stage):
            raise ValueError(
                "Variable speed compressors in compressor train have incompatible compressor charts."
                f" Stage {min_speed_per_stage.index(max(min_speed_per_stage)) + 1}'s minimum speed is higher"
                f" than max speed of stage {max_speed_per_stage.index(min(max_speed_per_stage)) + 1}"
            )
        return stages

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
