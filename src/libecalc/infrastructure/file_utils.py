import enum
from collections.abc import Callable
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd
from orjson import orjson

from libecalc.common.datetime.utils import DateTimeFormats
from libecalc.common.logger import logger
from libecalc.presentation.json_result.result import ComponentResult, EcalcModelResult
from libecalc.presentation.simple_result import SimpleResultData


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
    float_formatter: Callable | str | None = "%20.5f",
    date_format: str | None = None,
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


def to_json(result: ComponentResult | EcalcModelResult, simple_output: bool, date_format_option: int) -> str:
    """Dump result classes to json file

    Args:
        result: eCalc result data class
        simple_output: If true, will provide a simplified output format
        date_format_option:

    Returns:
        String dump of json output

    """
    data_to_dump = SimpleResultData.from_dto(result) if simple_output else result
    data = data_to_dump.model_dump(exclude_none=True, context={"include_timesteps": True})
    date_format = DateTimeFormats.get_format(date_format_option)

    def default_serializer(x: Any):
        if isinstance(x, datetime):
            return x.strftime(date_format)
        if isinstance(x, np.float64):
            return float(x)

        raise ValueError(f"Unable to serialize '{type(x)}'")

    # Using orjson to both allow custom date format and convert nan to null.
    # NaN to null is not supported by json module.
    # Custom date format is not supported by pydantic -> https://github.com/pydantic/pydantic/issues/7143
    return orjson.dumps(
        data,
        default=default_serializer,
        option=orjson.OPT_PASSTHROUGH_DATETIME | orjson.OPT_INDENT_2 | orjson.OPT_NON_STR_KEYS,
    ).decode()


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
        df = pd.DataFrame(index=results.periods.start_dates)
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
