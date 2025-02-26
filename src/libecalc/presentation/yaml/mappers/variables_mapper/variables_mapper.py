from dataclasses import dataclass
from datetime import datetime

from libecalc.common.logger import logger
from libecalc.common.time_utils import Periods
from libecalc.common.variables import VariablesMap
from libecalc.presentation.yaml.domain.time_series_provider import TimeSeriesProvider
from libecalc.presentation.yaml.yaml_models.yaml_model import YamlValidator
from libecalc.presentation.yaml.yaml_types.yaml_variable import (
    YamlSingleVariable,
    YamlVariable,
)


class InvalidVariablesException(Exception):
    def __init__(self, message: str):
        super().__init__(message)


@dataclass
class VariableProcessor:
    reference_id: str
    variable: YamlVariable

    @property
    def required_variables(self):
        if isinstance(self.variable, YamlSingleVariable):
            return self.variable.value.variables
        else:
            return {variable for expression in self.variable.values() for variable in expression.value.variables}

    def process(self, variables: dict[str, list[float]], periods: Periods) -> list[float]:
        if isinstance(self.variable, YamlSingleVariable):
            return list(self.variable.value.evaluate(variables, fill_length=len(periods)))
        else:
            variable_periods = Periods.create_periods(sorted(self.variable), include_before=False)
            processed_expressions = {
                period: variable.value.evaluate(variables, fill_length=len(periods))
                for period, variable in zip(variable_periods, self.variable.values())
            }

            variable_result = []
            should_warn_about_fill_value = False
            for i, period in enumerate(periods):
                variable_period = variable_periods.get_period(period)
                if variable_period in processed_expressions.keys():
                    variable_result.append(processed_expressions[variable_period][i])
                else:
                    # Fill value before variable is defined
                    variable_result.append(0.0)
                    should_warn_about_fill_value = True

            if should_warn_about_fill_value:
                logger.warning(
                    f"Variable {self.reference_id} is not defined for all time steps. Using 0.0 as fill value. "
                    f"Variable start: {sorted(self.variable)[0]}, time vector start: {periods.first_date}"
                )

            return variable_result


def _evaluate_variables(variables: dict[str, YamlVariable], variables_map: VariablesMap) -> VariablesMap:
    variables_to_process = [
        VariableProcessor(reference_id=f"$var.{reference_id}", variable=variable)
        for reference_id, variable in variables.items()
    ]
    processed_variables = {**variables_map.variables}

    did_process_variable = True
    while len(variables_to_process) > 0 and did_process_variable:
        did_process_variable = False  # Reset
        for variable in variables_to_process:
            is_required_variables_processed = all(
                required_variable in processed_variables for required_variable in variable.required_variables
            )
            if is_required_variables_processed:
                processed_variables[variable.reference_id] = variable.process(
                    variables=processed_variables,
                    periods=variables_map.periods,
                )
                variables_to_process.remove(variable)
                did_process_variable = True

    has_unsolvable_variables = len(variables_to_process) != 0
    if has_unsolvable_variables:
        missing_references = sorted(
            {
                reference_id
                for variable in variables_to_process
                for reference_id in variable.required_variables
                if reference_id not in processed_variables
            }
        )
        unsolvable_variables = sorted([variable.reference_id for variable in variables_to_process])
        raise InvalidVariablesException(
            f"Could not evaluate all variables, unable to resolve references in {', '.join(unsolvable_variables)}. "
            f"Missing references are {', '.join(missing_references)}"
        )

    return VariablesMap(variables=processed_variables, time_vector=variables_map.time_vector)


def map_yaml_to_variables(
    configuration: YamlValidator, time_series_provider: TimeSeriesProvider, global_time_vector: list[datetime]
) -> VariablesMap:
    variables = {}
    time_series_list = [
        time_series_provider.get_time_series(time_series_reference)
        for time_series_reference in time_series_provider.get_time_series_references()
    ]
    period_start_dates = global_time_vector[:-1]
    for time_series in time_series_list:
        variables[time_series.reference_id] = time_series.fit_to_time_vector(period_start_dates).series

    return _evaluate_variables(
        configuration.variables,
        variables_map=VariablesMap(variables=variables, time_vector=global_time_vector),
    )
