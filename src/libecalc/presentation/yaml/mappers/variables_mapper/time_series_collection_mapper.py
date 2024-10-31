import re
from datetime import datetime
from typing import Union

import pandas

from libecalc.common.errors.exceptions import InvalidResourceException
from libecalc.presentation.yaml.resource import Resource
from libecalc.presentation.yaml.yaml_keywords import EcalcYamlKeywords


def _parse_date(date_input: Union[int, str]) -> datetime:
    """
    Parse timeseries input:

    - Integer gets interpreted as year
    - Starting with YYYY.xx.xx, then we assume ISO 8601
    - Other than that, we assume a day-first format (e.g. Norwegian: DD.MM.YYYY)
    """
    # Columns with integers as dates are interpreted as year
    if isinstance(date_input, int):
        return datetime(date_input, 1, 1)

    date_split = re.split(r"\D+", date_input)
    if len(date_split[0]) == 4:
        return pandas.to_datetime(date_input).to_pydatetime()
    else:
        return pandas.to_datetime(date_input, dayfirst=True).to_pydatetime()


def parse_time_vector(time_vector: list[Union[int, str]]) -> list[datetime]:
    return [_parse_date(date_input) for date_input in time_vector]


def parse_time_series_from_resource(resource: Resource):
    time_series_resource_headers = resource.get_headers()

    if len(time_series_resource_headers) == 0:
        raise InvalidResourceException("Invalid resource", "Resource must at least have one column")

    if EcalcYamlKeywords.date in time_series_resource_headers:
        # Find the column named "DATE" and use that as time vector
        time_vector = resource.get_column(EcalcYamlKeywords.date)
        headers = [header for header in time_series_resource_headers if header != EcalcYamlKeywords.date]
    else:
        # Legacy: support random names for time vector as long as it is the first column
        time_vector = resource.get_column(time_series_resource_headers[0])
        headers = time_series_resource_headers[1:]

    return parse_time_vector(time_vector), headers
