from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List

from libecalc import dto
from libecalc.common.logger import logger
from libecalc.common.time_utils import Periods
from libecalc.dto import VariablesMap
from libecalc.presentation.yaml.mappers.variables_mapper.time_series_collection_mapper import (
    TimeSeriesCollectionMapper,
)
from libecalc.presentation.yaml.mappers.variables_mapper.timeseries_utils import (
    fit_time_series_to_time_vector,
    get_global_time_vector,
)
from libecalc.presentation.yaml.yaml_entities import Resources
from libecalc.presentation.yaml.yaml_models.pyyaml_yaml_model import PyYamlYamlModel
from libecalc.presentation.yaml.yaml_types.yaml_variable import (
    YamlSingleVariable,
    YamlVariable,
)


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

    def process(self, variables: Dict[str, List[float]], time_vector: List[datetime]) -> List[float]:
        if isinstance(self.variable, YamlSingleVariable):
            return list(self.variable.value.evaluate(variables, fill_length=len(time_vector)))
        else:
            processed_expressions = {
                time: variable.value.evaluate(variables, fill_length=len(time_vector))
                for time, variable in self.variable.items()
            }
            sorted_times = sorted(processed_expressions)

            periods = Periods.create_periods(sorted_times)

            variable_result = []
            should_warn_about_fill_value = False
            for current_index, time_step in enumerate(time_vector):
                period = periods.get_period(time_step)
                if period.start in processed_expressions:
                    variable_result.append(processed_expressions[period.start][current_index])
                else:
                    # Fill value before variable is defined
                    variable_result.append(0.0)
                    should_warn_about_fill_value = True

            if should_warn_about_fill_value:
                logger.warning(
                    f"Variable {self.reference_id} is not defined for all time steps. Using 0.0 as fill value. "
                    f"Variable start: {sorted_times[0]}, time vector start: {min(time_vector)}"
                )

            return variable_result


def _evaluate_variables(variables: Dict[str, YamlVariable], variables_map: VariablesMap) -> VariablesMap:
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
                    time_vector=variables_map.time_vector,
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
        raise ValueError(
            f"Could not evaluate all variables, unable to resolve references in {', '.join(unsolvable_variables)}. "
            f"Missing references are {', '.join(missing_references)}"
        )

    return VariablesMap(variables=processed_variables, time_vector=variables_map.time_vector)


def map_yaml_to_variables(
    configuration: PyYamlYamlModel,
    resources: Resources,
    result_options: dto.ResultOptions,
) -> dto.VariablesMap:
    timeseries_collections = [
        TimeSeriesCollectionMapper(resources).from_yaml_to_dto(timeseries.model_dump(by_alias=True))
        for timeseries in configuration.time_series
    ]

    global_time_vector = get_global_time_vector(
        time_series_collections=timeseries_collections,
        start=configuration.start,
        end=configuration.end,
        frequency=result_options.output_frequency,
        additional_dates=configuration.dates,
    )

    variables = {}
    for timeseries_collection in timeseries_collections:
        timeseries_list = timeseries_collection.time_series
        for timeseries in timeseries_list:
            variables[timeseries.reference_id] = fit_time_series_to_time_vector(
                time_series=timeseries,
                time_vector=global_time_vector,
                extrapolate_outside_defined_time_interval=timeseries_collection.extrapolate_outside_defined_time_interval,
                interpolation_type=timeseries_collection.interpolation_type,
            )

    return _evaluate_variables(
        configuration.variables, variables_map=VariablesMap(variables=variables, time_vector=global_time_vector)
    )
