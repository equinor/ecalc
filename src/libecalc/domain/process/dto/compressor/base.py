from typing import Literal, Union

from libecalc.common.consumer_type import ConsumerType
from libecalc.common.energy_model_type import EnergyModelType
from libecalc.domain.process.dto.base import ConsumerFunction, EnergyModel, EnergyUsageType
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

    def __init__(
        self,
        energy_usage_adjustment_constant: float,
        energy_usage_adjustment_factor: float,
        compressor_train: (
            CompressorSampled
            | CompressorTrainSimplifiedWithKnownStages
            | CompressorTrainSimplifiedWithUnknownStages
            | SingleSpeedCompressorTrain
            | VariableSpeedCompressorTrain
            | VariableSpeedCompressorTrainMultipleStreamsAndPressures
        ),
        turbine: Turbine,
    ):
        super().__init__(energy_usage_adjustment_constant, energy_usage_adjustment_factor)
        self.compressor_train = compressor_train
        self.turbine = turbine


CompressorModelTypes = Union[
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
    # Todo: add pressure_control_first_part, pressure_control_last_part and stage_number_interstage_pressure
    # TODO: validate power loss factor wrt energy usage type
    # validate energy function has the same energy_usage_type

    def __init__(
        self,
        energy_usage_type: EnergyUsageType,
        model: CompressorModelTypes,
        rate_standard_m3_day: Expression | list[Expression],
        condition: Expression | None = None,
        power_loss_factor: Expression | None = None,
        suction_pressure: Expression | None = None,
        discharge_pressure: Expression | None = None,
        interstage_control_pressure: Expression | None = None,
    ):
        super().__init__(typ=self.typ, energy_usage_type=energy_usage_type, condition=condition)
        self.model = model
        self.rate_standard_m3_day = convert_expressions(rate_standard_m3_day)
        self.power_loss_factor = convert_expression(power_loss_factor)
        self.suction_pressure = convert_expression(suction_pressure)
        self.discharge_pressure = convert_expression(discharge_pressure)
        self.interstage_control_pressure = convert_expression(interstage_control_pressure)
