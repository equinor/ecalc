from typing import Any

from libecalc import dto
from libecalc.common.logger import logger
from libecalc.core.models.compressor.base import (
    CompressorModel,
    CompressorWithTurbineModel,
)
from libecalc.core.models.compressor.sampled import CompressorModelSampled
from libecalc.core.models.compressor.train.fluid import FluidStream
from libecalc.core.models.compressor.train.simplified_train import (
    CompressorTrainSimplifiedKnownStages,
    CompressorTrainSimplifiedUnknownStages,
)
from libecalc.core.models.compressor.train.single_speed_compressor_train_common_shaft import (
    SingleSpeedCompressorTrainCommonShaft,
)
from libecalc.core.models.compressor.train.types import (
    FluidStreamObjectForMultipleStreams,
)
from libecalc.core.models.compressor.train.variable_speed_compressor_train_common_shaft import (
    VariableSpeedCompressorTrainCommonShaft,
)
from libecalc.core.models.compressor.train.variable_speed_compressor_train_common_shaft_multiple_streams_and_pressures import (
    VariableSpeedCompressorTrainCommonShaftMultipleStreamsAndPressures,
)
from libecalc.core.models.turbine import TurbineModel
from libecalc.dto.types import EnergyModelType


def _create_variable_speed_compressor_train_multiple_streams_and_pressures_stream(
    stream_data: dto.MultipleStreamsAndPressureStream,
    stream_references: dict,
) -> FluidStreamObjectForMultipleStreams:
    is_inlet_stream = stream_data.typ == dto.types.FluidStreamType.INGOING
    return FluidStreamObjectForMultipleStreams(
        name=stream_data.name,
        fluid=FluidStream(fluid_model=stream_data.fluid_model) if stream_data.fluid_model else None,
        is_inlet_stream=is_inlet_stream,
        connected_to_stage_no=stream_references[stream_data.name],
    )


def _create_compressor_train_simplified_with_known_stages(
    compressor_model_dto: dto.CompressorTrainSimplifiedWithKnownStages,
) -> CompressorTrainSimplifiedKnownStages:
    # Energy usage adjustment not supported for this model (yet)
    # Issue error if factors are not default (and not changing the energy usage result)
    return CompressorTrainSimplifiedKnownStages(
        data_transfer_object=compressor_model_dto,
    )


def _create_compressor_with_turbine(
    compressor_model_dto: dto.CompressorWithTurbine,
) -> CompressorWithTurbineModel:
    return CompressorWithTurbineModel(
        data_transfer_object=compressor_model_dto,
        compressor_energy_function=create_compressor_model(compressor_model_dto.compressor_train),
        turbine_model=TurbineModel(data_transfer_object=compressor_model_dto.turbine),
    )


def _create_turbine(turbine_dto: dto.Turbine) -> TurbineModel:
    return TurbineModel(data_transfer_object=turbine_dto)


def _create_single_speed_compressor_train(
    compressor_model_dto: dto.SingleSpeedCompressorTrain,
) -> SingleSpeedCompressorTrainCommonShaft:
    return SingleSpeedCompressorTrainCommonShaft(
        data_transfer_object=compressor_model_dto,
    )


def _create_variable_speed_compressor_train(
    compressor_model_dto: dto.VariableSpeedCompressorTrain,
) -> VariableSpeedCompressorTrainCommonShaft:
    return VariableSpeedCompressorTrainCommonShaft(
        data_transfer_object=compressor_model_dto,
    )


def _create_variable_speed_compressor_train_multiple_streams_and_pressures(
    compressor_model_dto: dto.VariableSpeedCompressorTrainMultipleStreamsAndPressures,
) -> VariableSpeedCompressorTrainCommonShaftMultipleStreamsAndPressures:
    return VariableSpeedCompressorTrainCommonShaftMultipleStreamsAndPressures(
        data_transfer_object=compressor_model_dto,
        streams=[
            _create_variable_speed_compressor_train_multiple_streams_and_pressures_stream(
                stream_specification_dto, compressor_model_dto.stream_references
            )
            for stream_specification_dto in compressor_model_dto.streams
        ],
    )


def _create_compressor_train_simplified_with_unknown_stages(
    compressor_model_dto: dto.CompressorTrainSimplifiedWithUnknownStages,
) -> CompressorTrainSimplifiedUnknownStages:
    return CompressorTrainSimplifiedUnknownStages(data_transfer_object=compressor_model_dto)


def _create_compressor_sampled(compressor_model_dto: dto.CompressorSampled) -> CompressorModelSampled:
    return CompressorModelSampled(data_transfer_object=compressor_model_dto)


facility_model_map = {
    EnergyModelType.COMPRESSOR_SAMPLED: _create_compressor_sampled,
    EnergyModelType.COMPRESSOR_TRAIN_SIMPLIFIED_WITH_KNOWN_STAGES: _create_compressor_train_simplified_with_known_stages,
    EnergyModelType.COMPRESSOR_TRAIN_SIMPLIFIED_WITH_UNKNOWN_STAGES: _create_compressor_train_simplified_with_unknown_stages,
    EnergyModelType.VARIABLE_SPEED_COMPRESSOR_TRAIN_COMMON_SHAFT: _create_variable_speed_compressor_train,
    EnergyModelType.VARIABLE_SPEED_COMPRESSOR_TRAIN_MULTIPLE_STREAMS_AND_PRESSURES: _create_variable_speed_compressor_train_multiple_streams_and_pressures,
    EnergyModelType.SINGLE_SPEED_COMPRESSOR_TRAIN_COMMON_SHAFT: _create_single_speed_compressor_train,
    EnergyModelType.COMPRESSOR_WITH_TURBINE: _create_compressor_with_turbine,
    EnergyModelType.TURBINE: _create_turbine,
}


def _invalid_compressor_model_type(compressor_model_dto: Any) -> None:
    try:
        msg = f"Unsupported energy model type: {compressor_model_dto.typ}."
        logger.error(msg)
        raise TypeError(msg)
    except AttributeError as e:
        msg = "Unsupported energy model type."
        logger.exception(msg)
        raise TypeError(msg) from e


def create_compressor_model(compressor_model_dto: dto.CompressorModel) -> CompressorModel:
    return facility_model_map.get(compressor_model_dto.typ, _invalid_compressor_model_type)(
        compressor_model_dto=compressor_model_dto,
    )  # type: ignore[call-arg]
