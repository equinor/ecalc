from libecalc.domain.process.compressor.core.sampled import CompressorModelSampled
from libecalc.domain.process.compressor.core.train.types import FluidStreamObjectForMultipleStreams
from libecalc.domain.process.compressor.core.train.variable_speed_compressor_train_common_shaft import (
    VariableSpeedCompressorTrainCommonShaft,
)
from libecalc.domain.process.compressor.core.train.variable_speed_compressor_train_common_shaft_multiple_streams_and_pressures import (
    VariableSpeedCompressorTrainCommonShaftMultipleStreamsAndPressures,
)
from libecalc.domain.process.compressor.core.utils import map_compressor_train_stage_to_domain
from libecalc.domain.process.compressor.dto import (
    CompressorSampled,
    VariableSpeedCompressorTrain,
    VariableSpeedCompressorTrainMultipleStreamsAndPressures,
)
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


def _create_variable_speed_compressor_train(
    compressor_model_dto: VariableSpeedCompressorTrain,
) -> VariableSpeedCompressorTrainCommonShaft:
    fluid_factory = _create_fluid_factory(compressor_model_dto.fluid_model)
    if fluid_factory is None:
        raise ValueError("Fluid model is required for compressor train")
    return VariableSpeedCompressorTrainCommonShaft(
        fluid_factory=fluid_factory,
        energy_usage_adjustment_constant=compressor_model_dto.energy_usage_adjustment_constant,
        energy_usage_adjustment_factor=compressor_model_dto.energy_usage_adjustment_factor,
        stages=compressor_model_dto.stages,
        pressure_control=compressor_model_dto.pressure_control,
        calculate_max_rate=compressor_model_dto.calculate_max_rate,
        maximum_power=compressor_model_dto.maximum_power,
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

    stages = [map_compressor_train_stage_to_domain(stage) for stage in compressor_model_dto.stages]
    has_interstage_pressure = any(stage.interstage_pressure_control is not None for stage in stages)
    stage_number_interstage_pressure = (
        [i for i, stage in enumerate(stages) if stage.interstage_pressure_control is not None][0]
        if has_interstage_pressure
        else None
    )
    return VariableSpeedCompressorTrainCommonShaftMultipleStreamsAndPressures(
        fluid_factory=fluid_factory_train_inlet,
        streams=[
            _create_variable_speed_compressor_train_multiple_streams_and_pressures_stream(
                stream_specification_dto, compressor_model_dto.stream_references
            )
            for stream_specification_dto in compressor_model_dto.streams
        ],
        energy_usage_adjustment_constant=compressor_model_dto.energy_usage_adjustment_constant,
        energy_usage_adjustment_factor=compressor_model_dto.energy_usage_adjustment_factor,
        stages=stages,
        calculate_max_rate=compressor_model_dto.calculate_max_rate,
        maximum_power=compressor_model_dto.maximum_power,
        pressure_control=compressor_model_dto.pressure_control,
        stage_number_interstage_pressure=stage_number_interstage_pressure,
    )


def _create_compressor_sampled(compressor_model_dto: CompressorSampled) -> CompressorModelSampled:
    return CompressorModelSampled(
        energy_usage_adjustment_constant=compressor_model_dto.energy_usage_adjustment_constant,
        energy_usage_adjustment_factor=compressor_model_dto.energy_usage_adjustment_factor,
        energy_usage_type=compressor_model_dto.energy_usage_type,
        energy_usage_values=compressor_model_dto.energy_usage_values,
        rate_values=compressor_model_dto.rate_values,
        suction_pressure_values=compressor_model_dto.suction_pressure_values,
        discharge_pressure_values=compressor_model_dto.discharge_pressure_values,
        power_interpolation_values=compressor_model_dto.power_interpolation_values,
    )
