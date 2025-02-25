import numpy

from libecalc.common.energy_usage_type import EnergyUsageType
from libecalc.domain.infrastructure.energy_components.legacy_consumer.consumer_function.consumer_tabular_energy_function import (
    TabulatedConsumerFunction,
)
from libecalc.domain.process.core.tabulated import (
    ConsumerTabularEnergyFunction,
    Variable,
    VariableExpression,
)
from libecalc.domain.process.dto import TabulatedConsumerFunction as TabulatedConsumerFunctionDTO


def _get_column(data: list[list], headers: list[str], header: str) -> list:
    return data[headers.index(header)]


def create_tabulated_consumer_function(model_dto: TabulatedConsumerFunctionDTO) -> TabulatedConsumerFunction:
    function_value_header = model_dto.energy_usage_type
    data = model_dto.model.data
    headers = model_dto.model.headers

    function_values = numpy.array(_get_column(data, headers, function_value_header))

    variable_headers = [header for header in model_dto.model.headers if header != function_value_header]
    variable_values = [
        _get_column(data=data, headers=headers, header=variable_header) for variable_header in variable_headers
    ]
    variable_values_as_array = [numpy.array(variable_value) for variable_value in variable_values]
    variables = [Variable(name=name, values=values) for name, values in zip(variable_headers, variable_values_as_array)]

    # required to set either "FUEL" or "POWER" (according to doc) and now also verified in validation
    energy_usage_type: EnergyUsageType = EnergyUsageType.FUEL if "FUEL" in headers else EnergyUsageType.POWER

    tabulated_energy_function = ConsumerTabularEnergyFunction(
        function_values=function_values,
        variables=variables,
        energy_usage_adjustment_constant=model_dto.model.energy_usage_adjustment_constant,
        energy_usage_adjustment_factor=model_dto.model.energy_usage_adjustment_factor,
        energy_usage_type=energy_usage_type,
    )

    return TabulatedConsumerFunction(
        tabulated_energy_function=tabulated_energy_function,
        variables_expressions=[
            VariableExpression(
                name=variable.name,
                expression=variable.expression,
            )
            for variable in model_dto.variables
        ],
        condition_expression=model_dto.condition,
        power_loss_factor_expression=model_dto.power_loss_factor,
    )
