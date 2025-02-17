import logging
from datetime import datetime

import pandas as pd

from libecalc.common.errors.exceptions import InvalidResourceException
from libecalc.presentation.yaml.resource import Resource
from libecalc.presentation.yaml.validation_errors import ValidationError
from libecalc.presentation.yaml.yaml_keywords import EcalcYamlKeywords

logger = logging.getLogger(__name__)


def parse_time_vector(date_input: list[int | str]) -> list[datetime]:
    """Parse entire timeseries in a single format.

    Args:
        date_input: Dates in unknown format.

    Returns:
        Consistent dates.

    Raises:
        ValidationError:
            If dates do not match any of the given patterns.
            If dates are in an inconsistent format.
    """
    date_patterns = {
        # Only year supplied (YYYY e.g. 1996).
        "YEAR_ONLY": r"\d{4}",
        # ISO8601 date only e.g. '2024-01-31', '2024-12-01'.
        "ISO8601_date": r"(\d{4})(\.|\/|-)(1[0-2]|0?[1-9])\2(3[01]|[12][0-9]|0?[1-9])",
        # ISO8601 date and time e.g. '2024-01-31 13:37:59', '2024-12-01 23:59:59'.
        "ISO8601_datetime": r"(\d{4})(\.|\/|-)(1[0-2]|0?[1-9])\2(3[01]|[12][0-9]|0?[1-9])((\s|T)(\d{2}:){2}\d{2})",
        # European standard (day first) e.g. '31-01-2024', '1/12/2024', '01.12.2024'.
        "EU_date": r"(3[01]|[12][0-9]|0?[1-9])(\.|\/|-)(1[0-2]|0?[1-9])\2(\d{4})",
        # European date with time, e.g. e.g. '31-01-2024 13:37:59', '1/12/2024 10:30:00', '01.01.2024 13:37')
        "EU_datetime": r"(3[01]|[12][0-9]|0?[1-9])(\.|\/|-)(1[0-2]|0?[1-9])\2(\d{4})((\s|T)(\d{2}):(\d{2})(:\d{2})?)",
        # Explicitly not supported!
        "ISO8601_optional_time": r"(\d{4})(\.|\/|-)(1[0-2]|0?[1-9])\2(3[01]|[12][0-9]|0?[1-9])((\s|T)(\d{2}:){2}\d{2})?",
        "EU_optional_time": r"(3[01]|[12][0-9]|0?[1-9])(\.|\/|-)(1[0-2]|0?[1-9])\2(\d{4})((\s)(\d{2}):(\d{2})(:\d{2})?)?",
        # US standard date (month first), e.g. '12-31-2024', '9/1/2024'.
        "US_date": r"(1[0-2]|0?[1-9])(\.|\/|-)(3[01]|[12][0-9]|0?[1-9])\2(\d{4})",
        # US standard date with time (e.g. '12-31-2024 01:37:59', '9.9.2024 1:13')
        "US_datetime": r"(1[0-2]|0?[1-9])(\.|\/|-)(3[01]|[12][0-9]|0?[1-9])\2(\d{4})((\s|T)(\d{1,2}):(\d{2})(:\d{2})?)",
        "US_optional_time": r"(1[0-2]|0?[1-9])(\.|\/|-)(3[01]|[12][0-9]|0?[1-9])\2(\d{4})((\s|T)(\d{1,2})\:(\d{2})(:\d{2})?)?",
    }
    # Replace '/', '\' and '.', with '-' for consistency.
    check_dates: pd.Series = pd.Series(date_input).astype(str)
    date_list: list[str] = check_dates.str.replace(r"/|\.|\\", "-", regex=True).tolist()

    if check_dates.str.fullmatch(date_patterns["YEAR_ONLY"]).all():
        return pd.to_datetime(date_list, format="%Y", errors="raise").to_pydatetime().tolist()
    if check_dates.str.fullmatch(date_patterns["ISO8601_datetime"]).all():
        return pd.to_datetime(date_list, format="ISO8601", errors="raise").to_pydatetime().tolist()
    if check_dates.str.fullmatch(date_patterns["ISO8601_date"]).all():
        return pd.to_datetime(date_list, format="ISO8601", errors="raise").to_pydatetime().tolist()
    if check_dates.str.fullmatch(date_patterns["EU_datetime"]).all():
        return pd.to_datetime(date_list, dayfirst=True, errors="raise").to_pydatetime().tolist()
    if check_dates.str.fullmatch(date_patterns["EU_date"]).all():
        return pd.to_datetime(date_list, dayfirst=True, errors="raise").to_pydatetime().tolist()

    logger.debug("Unexpected datetime-format encountered in data:\n%s", date_input)

    if check_dates.str.fullmatch(date_patterns["ISO8601_optional_time"]).all():
        raise ValidationError("A mix of only dates and dates with time is not valid, ensure datetimes are consistent.")
    if check_dates.str.fullmatch(date_patterns["EU_optional_time"]).all():
        raise ValidationError("A mix of only dates and dates with time is not valid, ensure datetimes are consistent.")
    if check_dates.str.fullmatch(date_patterns["US_optional_time"]).all():
        if check_dates.str.fullmatch(date_patterns["US_date"]).all():
            raise ValidationError("Month first (US style) dates are not supported.")
        if check_dates.str.fullmatch(date_patterns["US_datetime"]).all():
            raise ValidationError("Month first (US style) dates are not supported.")
        raise ValidationError(
            "Month first (US style) dates are not supported. "
            "Got a mix of only dates and dates with time. Please also ensure datetimes are consistent."
        )
    if check_dates.str.contains(r"(am|pm|AM|PM)$", regex=True).any():
        raise ValidationError("AM/PM are not supported in dates, only 24 hour clock is valid.")
    raise ValidationError(
        "The provided date doesn't match any of the accepted date formats, or contains inconsistently formatted dates."
    )


def parse_time_series_from_resource(resource: Resource) -> tuple[list[datetime], list[str]]:
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
