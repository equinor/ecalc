from typing import List, Literal, Optional, Union

from pydantic import field_validator

from libecalc.dto.models.compressor.compressor_model import CompressorModel
from libecalc.dto.models.consumer_function import ConsumerFunction
from libecalc.dto.types import ConsumerType
from libecalc.dto.utils.validators import convert_expression, convert_expressions
from libecalc.expression import Expression


class CompressorConsumerFunction(ConsumerFunction):
    typ: Literal[ConsumerType.COMPRESSOR] = ConsumerType.COMPRESSOR
    power_loss_factor: Optional[Expression] = None
    model: CompressorModel
    rate_standard_m3_day: Union[Expression, List[Expression]]
    suction_pressure: Optional[Expression] = None
    discharge_pressure: Optional[Expression] = None
    interstage_control_pressure: Optional[Expression] = None
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
