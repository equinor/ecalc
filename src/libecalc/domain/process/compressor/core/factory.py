from typing import Any

from libecalc.common.energy_model_type import EnergyModelType
from libecalc.common.logger import logger
from libecalc.domain.infrastructure.energy_components.turbine import Turbine
from libecalc.domain.process.compressor.core.base import CompressorModel, CompressorWithTurbineModel
from libecalc.domain.process.compressor.core.sampled import CompressorModelSampled
from libecalc.domain.process.compressor.core.train.simplified_train import (
    CompressorTrainSimplifiedKnownStages,
    CompressorTrainSimplifiedUnknownStages,
)
from libecalc.domain.process.compressor.core.train.single_speed_compressor_train_common_shaft import (
    SingleSpeedCompressorTrainCommonShaft,
)
from libecalc.domain.process.compressor.core.train.types import FluidStreamObjectForMultipleStreams
from libecalc.domain.process.compressor.core.train.variable_speed_compressor_train_common_shaft import (
    VariableSpeedCompressorTrainCommonShaft,
)
from libecalc.domain.process.compressor.core.train.variable_speed_compressor_train_common_shaft_multiple_streams_and_pressures import (
    VariableSpeedCompressorTrainCommonShaftMultipleStreamsAndPressures,
)
from libecalc.domain.process.compressor.dto import (
    CompressorSampled,
    CompressorTrainSimplifiedWithKnownStages,
    CompressorTrainSimplifiedWithUnknownStages,
    CompressorWithTurbine,
    SingleSpeedCompressorTrain,
    VariableSpeedCompressorTrain,
    VariableSpeedCompressorTrainMultipleStreamsAndPressures,
)
from libecalc.domain.process.compressor.dto.model_types import CompressorModelTypes as CompressorModelDTO
from libecalc.domain.process.value_objects.fluid_stream.fluid_factory import FluidFactoryInterface
from libecalc.domain.process.value_objects.fluid_stream.fluid_model import FluidModel
from libecalc.domain.process.value_objects.fluid_stream.multiple_streams_stream import (
    FluidStreamType,
    MultipleStreamsAndPressureStream,
)
from libecalc.infrastructure.neqsim_fluid_provider.neqsim_fluid_factory import NeqSimFluidFactory


def _create_fluid_factory(fluid_model: FluidModel | None) -> FluidFactoryInterface | None:
    """Create a fluid factory from a fluid model."""
    if fluid_model is None:
        return None
    return NeqSimFluidFactory(fluid_model)


def _create_variable_speed_compressor_train_multiple_streams_and_pressures_stream(
    stream_data: MultipleStreamsAndPressureStream,
    stream_references: dict,
) -> FluidStreamObjectForMultipleStreams:
    is_inlet_stream = stream_data.typ == FluidStreamType.INGOING
    return FluidStreamObjectForMultipleStreams(
        name=stream_data.name,
        fluid_model=stream_data.fluid_model,
        is_inlet_stream=is_inlet_stream,
        connected_to_stage_no=stream_references[stream_data.name],
    )


def _create_compressor_train_simplified_with_known_stages(
    compressor_model_dto: CompressorTrainSimplifiedWithKnownStages,
) -> CompressorTrainSimplifiedKnownStages:
    # Energy usage adjustment not supported for this model (yet)
    # Issue error if factors are not default (and not changing the energy usage result)
    fluid_factory = _create_fluid_factory(compressor_model_dto.fluid_model)
    if fluid_factory is None:
        raise ValueError("Fluid model is required for compressor train")
    return CompressorTrainSimplifiedKnownStages(
        data_transfer_object=compressor_model_dto,
        fluid_factory=fluid_factory,
    )


def _create_turbine(turbine_dto: Turbine) -> Turbine:
    return Turbine(
        loads=turbine_dto.loads,
        lower_heating_value=turbine_dto.lower_heating_value,
        efficiency_fractions=turbine_dto.efficiency_fractions,
        energy_usage_adjustment_constant=turbine_dto._energy_usage_adjustment_constant,
        energy_usage_adjustment_factor=turbine_dto._energy_usage_adjustment_factor,
    )


def _create_compressor_with_turbine(
    compressor_model_dto: CompressorWithTurbine,
) -> CompressorWithTurbineModel:
    return CompressorWithTurbineModel(
        energy_usage_adjustment_constant=compressor_model_dto.energy_usage_adjustment_constant,
        energy_usage_adjustment_factor=compressor_model_dto.energy_usage_adjustment_factor,
        compressor_energy_function=create_compressor_model(compressor_model_dto.compressor_train),
        turbine_model=_create_turbine(compressor_model_dto.turbine),
    )


def _create_single_speed_compressor_train(
    compressor_model_dto: SingleSpeedCompressorTrain,
) -> SingleSpeedCompressorTrainCommonShaft:
    fluid_factory = _create_fluid_factory(compressor_model_dto.fluid_model)
    if fluid_factory is None:
        raise ValueError("Fluid model is required for compressor train")
    return SingleSpeedCompressorTrainCommonShaft(
        data_transfer_object=compressor_model_dto,
        fluid_factory=fluid_factory,
    )


def _create_variable_speed_compressor_train(
    compressor_model_dto: VariableSpeedCompressorTrain,
) -> VariableSpeedCompressorTrainCommonShaft:
    fluid_factory = _create_fluid_factory(compressor_model_dto.fluid_model)
    if fluid_factory is None:
        raise ValueError("Fluid model is required for compressor train")
    return VariableSpeedCompressorTrainCommonShaft(
        data_transfer_object=compressor_model_dto,
        fluid_factory=fluid_factory,
    )


def _create_variable_speed_compressor_train_multiple_streams_and_pressures(
    compressor_model_dto: VariableSpeedCompressorTrainMultipleStreamsAndPressures,
) -> VariableSpeedCompressorTrainCommonShaftMultipleStreamsAndPressures:
    # Find the first inlet stream's fluid model for the train inlet
    fluid_model_train_inlet = None
    for stream in compressor_model_dto.streams:
        if stream.typ == FluidStreamType.INGOING and stream.fluid_model is not None:
            fluid_model_train_inlet = stream.fluid_model
            break

    # Fall back to dto fluid_model if no inlet stream has a fluid model
    if fluid_model_train_inlet is None:
        fluid_model_train_inlet = compressor_model_dto.fluid_model

    fluid_factory_train_inlet = _create_fluid_factory(fluid_model_train_inlet)
    if fluid_factory_train_inlet is None:
        raise ValueError("Fluid model is required for compressor train")

    return VariableSpeedCompressorTrainCommonShaftMultipleStreamsAndPressures(
        data_transfer_object=compressor_model_dto,
        fluid_factory=fluid_factory_train_inlet,
        streams=[
            _create_variable_speed_compressor_train_multiple_streams_and_pressures_stream(
                stream_specification_dto, compressor_model_dto.stream_references
            )
            for stream_specification_dto in compressor_model_dto.streams
        ],
    )


def _create_compressor_train_simplified_with_unknown_stages(
    compressor_model_dto: CompressorTrainSimplifiedWithUnknownStages,
) -> CompressorTrainSimplifiedUnknownStages:
    fluid_factory = _create_fluid_factory(compressor_model_dto.fluid_model)
    if fluid_factory is None:
        raise ValueError("Fluid model is required for compressor train")
    return CompressorTrainSimplifiedUnknownStages(
        data_transfer_object=compressor_model_dto,
        fluid_factory=fluid_factory,
    )


def _create_compressor_sampled(compressor_model_dto: CompressorSampled) -> CompressorModelSampled:
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


def create_compressor_model(compressor_model_dto: CompressorModelDTO) -> CompressorModel:
    return facility_model_map.get(compressor_model_dto.typ, _invalid_compressor_model_type)(  # type: ignore[operator]
        compressor_model_dto=compressor_model_dto,
    )
