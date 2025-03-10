from typing import Literal, Union

from pydantic import Field, field_validator

from libecalc.common.consumer_type import ConsumerType
from libecalc.common.energy_model_type import EnergyModelType
from libecalc.domain.process.dto.base import ConsumerFunction, EnergyModel
from libecalc.domain.process.dto.compressor.sampled import CompressorSampled
from libecalc.domain.process.dto.compressor.train import (
    CompressorTrainSimplifiedWithKnownStages,
    CompressorTrainSimplifiedWithUnknownStages,
    SingleSpeedCompressorTrain,
    VariableSpeedCompressorTrain,
    VariableSpeedCompressorTrainMultipleStreamsAndPressures,
)
from libecalc.domain.process.dto.turbine import Turbine
from libecalc.dto.utils.validators import convert_expression, convert_expressions
from libecalc.expression import Expression


class CompressorWithTurbine(EnergyModel):
    typ: Literal[EnergyModelType.COMPRESSOR_WITH_TURBINE] = EnergyModelType.COMPRESSOR_WITH_TURBINE
    compressor_train: (
        CompressorSampled
        | CompressorTrainSimplifiedWithKnownStages
        | CompressorTrainSimplifiedWithUnknownStages
        | SingleSpeedCompressorTrain
        | VariableSpeedCompressorTrain
        | VariableSpeedCompressorTrainMultipleStreamsAndPressures
    ) = Field(..., discriminator="typ")
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
    power_loss_factor: Expression | None = None
    model: CompressorModel = Field(..., discriminator="typ")
    rate_standard_m3_day: Expression | list[Expression]
    suction_pressure: Expression | None = None
    discharge_pressure: Expression | None = None
    interstage_control_pressure: Expression | None = None
    # Todo: add pressure_control_first_part, pressure_control_last_part and stage_number_interstage_pressure
    # TODO: validate power loss factor wrt energy usage type
    # validate energy function has the same energy_usage_type

    _convert_expressions = field_validator(
        "suction_pressure",
        "discharge_pressure",
        "power_loss_factor",
        "interstage_control_pressure",
        mode="before",
    )(convert_expression)
    _convert_rate_expressions = field_validator(
        "rate_standard_m3_day",
        mode="before",
    )(convert_expressions)
