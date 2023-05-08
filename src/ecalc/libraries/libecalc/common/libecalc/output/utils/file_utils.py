import enum
from typing import Callable, Optional, Union

import pandas as pd
from libecalc.common.io.utils import DateTimeFormats
from libecalc.common.logger import logger
from libecalc.dto.result import ComponentResult, EcalcModelResult


class OutputFormat(enum.Enum):
    CSV = "csv"
    JSON = "json"

    def __str__(self):
        return self.value


def dataframe_to_csv(
    df: pd.DataFrame,
    separator: str = ",",
    show_index: bool = True,
    float_formatter: Optional[Union[Callable, str]] = "%20.5f",
    date_format: Optional[str] = None,
) -> str:
    return df.to_csv(
        float_format=float_formatter,
        index=show_index,
        index_label="timesteps",
        encoding="utf-8",
        sep=separator,
        date_format=date_format,
    )


def to_json(result: Union[ComponentResult, EcalcModelResult], simple_output: bool, date_format_option: int) -> str:
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


def get_component_output(
    results: EcalcModelResult,
    component_name: str,
    output_format: OutputFormat,
    simple_output: bool,
    date_format_option: int,
) -> str:
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
            exit(0)

        component = components[int(selected_component_index)]

    if output_format == OutputFormat.JSON:
        return to_json(component, simple_output=simple_output, date_format_option=date_format_option)
    elif output_format == OutputFormat.CSV:
        df = component.to_dataframe()
        return dataframe_to_csv(df, date_format=DateTimeFormats.get_format(date_format_option))
