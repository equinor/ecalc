from typing import List, Literal, Optional

from pydantic import validator

from libecalc.dto.base import EcalcBaseModel
from libecalc.dto.models.base import ConsumerFunction
from libecalc.dto.models.sampled import EnergyModelSampled
from libecalc.dto.types import ConsumerType, EnergyModelType
from libecalc.dto.utils.validators import convert_expression
from libecalc.expression import Expression
from libecalc.presentation.yaml.yaml_keywords import EcalcYamlKeywords


class TabulatedData(EnergyModelSampled):
    typ: Literal[EnergyModelType.TABULATED] = EnergyModelType.TABULATED

    @validator("headers")
    def validate_headers(cls, headers: List[str]) -> List[str]:
        possible_headers = [
            EcalcYamlKeywords.consumer_tabular_fuel,
            EcalcYamlKeywords.consumer_tabular_power,
            EcalcYamlKeywords.consumer_function_rate,
            EcalcYamlKeywords.consumer_function_suction_pressure,
            EcalcYamlKeywords.consumer_function_discharge_pressure,
        ]
        required_energy_headers = len(headers) > 0 and (
            EcalcYamlKeywords.consumer_tabular_fuel in headers or EcalcYamlKeywords.consumer_tabular_power in headers
        )
        required_rate_header = len(headers) > 0 and EcalcYamlKeywords.consumer_function_rate in headers
        header_not_allowed = [header for header in headers if header not in possible_headers]

        if len(header_not_allowed) > 0:
            raise ValueError(
                f"TABULAR facility input type data does not support {header_not_allowed} as header. "
                f"Allowed headers are {possible_headers}."
            )
        elif not required_energy_headers:
            raise ValueError(
                f"TABULAR facility input type data must have a "
                f"{EcalcYamlKeywords.consumer_tabular_fuel} or {EcalcYamlKeywords.consumer_tabular_power} header"
            )
        elif not required_rate_header:
            raise ValueError(
                f"TABULAR facility input type data must have a {EcalcYamlKeywords.consumer_function_rate} header"
            )
        return headers


class Variables(EcalcBaseModel):
    name: str
    expression: Expression

    _convert_variable_expression = validator("expression", allow_reuse=True, pre=True)(convert_expression)


class TabulatedConsumerFunction(ConsumerFunction):
    typ: Literal[ConsumerType.TABULATED] = ConsumerType.TABULATED
    power_loss_factor: Optional[Expression]
    model: TabulatedData
    variables: List[Variables]

    _convert_to_expression = validator("power_loss_factor", allow_reuse=True, pre=True)(convert_expression)
