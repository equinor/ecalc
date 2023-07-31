import enum
import sys
from typing import Callable, Optional, Union

import pandas as pd
from libecalc.common.io.utils import DateTimeFormats
from libecalc.common.logger import logger
from libecalc.dto.result import ComponentResult, EcalcModelResult


class OutputFormat(enum.Enum):
    """Supported output file formats from eCalc"""

    CSV = "csv"
    JSON = "json"

    def __str__(self):
        """Dump enum to string"""
        return self.value


def dataframe_to_csv(
    df: pd.DataFrame,
    separator: str = ",",
    show_index: bool = True,
    float_formatter: Optional[Union[Callable, str]] = "%20.5f",
    date_format: Optional[str] = None,
) -> str:
    """Dump pandas dataframe to csv file

    Wraps pandas to_csv functionality, for more options see pandas docs

    Args:
        df: Dataframe to dump
        separator: value separator in out, defaults to ',' for csv
        show_index: if true, will include index in dump
        float_formatter:
        date_format:

    Returns:

    """
    return df.to_csv(
        float_format=float_formatter,
        index=show_index,
        index_label="timesteps",
        encoding="utf-8",
        sep=separator,
        date_format=date_format,
    )


def to_json(result: Union[ComponentResult, EcalcModelResult], simple_output: bool, date_format_option: int) -> str:
    """Dump result classes to json file

    Args:
        result: eCalc result data class
        simple_output: If true, will provide a simplified output format
        date_format_option:

    Returns:
        String dump of json output

    """
    date_format = DateTimeFormats.get_format(date_format_option)
    return (
        result.simple_result().json(
            indent=True,
            date_format=date_format,
            exclude_none=True,
        )
        if simple_output
        else result.json(
            indent=True,
            date_format=date_format,
            exclude_none=True,
        )
    )


def get_result_output(
    results: EcalcModelResult,
    output_format: OutputFormat,
    simple_output: bool,
    date_format_option: int,
) -> str:
    """Result output controller

    Output eCalc results in desired format and

    Args:
        results:
        output_format:
        simple_output: If true, will provide a simplified output format. Only supported for json format
        date_format_option:

    Returns:

    """
    if output_format == OutputFormat.JSON:
        return to_json(results, simple_output=simple_output, date_format_option=date_format_option)
    elif output_format == OutputFormat.CSV:
        df = pd.DataFrame(index=results.timesteps)
        for component in results.components:
            component_df = component.to_dataframe(
                prefix=component.name,
            )
            try:
                df = df.join(component_df)
            except ValueError:
                logger.warning(
                    f"Duplicate component names in result detected. Component name '{component.name}', "
                    f"component type '{component.componentType}'."
                )
                df = pd.concat([df, component_df], axis=1)
        return dataframe_to_csv(df.fillna("nan"), date_format=DateTimeFormats.get_format(date_format_option))
    else:
        raise ValueError(
            f"Invalid output format. Expected {OutputFormat.CSV} or {OutputFormat.JSON}, got '{output_format}'"
        )


def get_component_output(
    results: EcalcModelResult,
    component_name: str,
    output_format: OutputFormat,
    simple_output: bool,
    date_format_option: int,
) -> str:
    """Get eCalc output for a single component by name

    Args:
        results: Complete from eCalc model
        component_name: Name of component to output results from
        output_format: Format of output file, CSV and JSON is currently supported
        simple_output: If true, will provide a simplified output format. Only supported for json format
        date_format_option:

    Returns:

    """
    components = [component for component in results.components if component.name == component_name]

    if len(components) == 0:
        msg = f"Unable to find component with name '{component_name}'"
        logger.error(msg)
        raise ValueError(msg)
    elif len(components) == 1:
        component = components[0]
    else:
        print("Several components match this name\n")
        format_str = "{:<5} {:<18} {:<10}"
        print(format_str.format("index", "type", "name"))
        for index, component in enumerate(components):
            print(format_str.format(index, component.componentType.value, component.name))
        print()
        selected_component_index = input("Enter the index of the component you want to select (q to quit): ")
        if selected_component_index == "q":
            sys.exit(0)

        component = components[int(selected_component_index)]

    if output_format == OutputFormat.JSON:
        return to_json(component, simple_output=simple_output, date_format_option=date_format_option)
    elif output_format == OutputFormat.CSV:
        df = component.to_dataframe()
        return dataframe_to_csv(df, date_format=DateTimeFormats.get_format(date_format_option))
    else:
        raise ValueError(
            f"Invalid output format. Expected {OutputFormat.CSV} or {OutputFormat.JSON}, got '{output_format}'"
        )
