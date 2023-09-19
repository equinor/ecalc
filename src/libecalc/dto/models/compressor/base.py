from typing import List, Literal, Optional, Union

from libecalc.dto.models.base import ConsumerFunction, EnergyModel
from libecalc.dto.models.compressor.sampled import CompressorSampled
from libecalc.dto.models.compressor.train import (
    CompressorTrainSimplifiedWithKnownStages,
    CompressorTrainSimplifiedWithUnknownStages,
    SingleSpeedCompressorTrain,
    VariableSpeedCompressorTrain,
    VariableSpeedCompressorTrainMultipleStreamsAndPressures,
)
from libecalc.dto.models.turbine import Turbine
from libecalc.dto.types import ConsumerType, EnergyModelType
from libecalc.dto.utils.validators import convert_expression, convert_expressions
from libecalc.expression import Expression
from pydantic import Field, validator


class CompressorWithTurbine(EnergyModel):
    typ: Literal[EnergyModelType.COMPRESSOR_WITH_TURBINE] = EnergyModelType.COMPRESSOR_WITH_TURBINE
    compressor_train: Union[
        CompressorSampled,
        CompressorTrainSimplifiedWithKnownStages,
        CompressorTrainSimplifiedWithUnknownStages,
        SingleSpeedCompressorTrain,
        VariableSpeedCompressorTrain,
        VariableSpeedCompressorTrainMultipleStreamsAndPressures,
    ] = Field(..., discriminator="typ")
    turbine: Turbine


CompressorModel = Union[
    CompressorSampled,
    CompressorTrainSimplifiedWithUnknownStages,
    CompressorTrainSimplifiedWithKnownStages,
    CompressorWithTurbine,
    VariableSpeedCompressorTrain,
    SingleSpeedCompressorTrain,
    VariableSpeedCompressorTrainMultipleStreamsAndPressures,
]


class CompressorConsumerFunction(ConsumerFunction):
    typ: Literal[ConsumerType.COMPRESSOR] = ConsumerType.COMPRESSOR
    power_loss_factor: Optional[Expression]
    model: CompressorModel = Field(..., discriminator="typ")
    rate_standard_m3_day: Union[Expression, List[Expression]]
    suction_pressure: Optional[Expression]
    discharge_pressure: Optional[Expression]
    interstage_control_pressure: Optional[Expression]
    # Todo: add pressure_control_first_part, pressure_control_last_part and stage_number_interstage_pressure
    # TODO: validate power loss factor wrt energy usage type
    # validate energy function has the same energy_usage_type

    _convert_expressions = validator(
        "suction_pressure",
        "discharge_pressure",
        "power_loss_factor",
        "interstage_control_pressure",
        allow_reuse=True,
        pre=True,
    )(convert_expression)
    _convert_rate_expressions = validator(
        "rate_standard_m3_day",
        allow_reuse=True,
        pre=True,
    )(convert_expressions)
