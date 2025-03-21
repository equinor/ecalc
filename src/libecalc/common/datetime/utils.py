from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel

from libecalc.common.logger import logger
from libecalc.common.utils.rates import TimeSeries


class DateTimeFormats(str, Enum):
    date_format_iso_8601 = "%Y-%m-%d"
    date_format_iso_8601_no_dash = "%Y%m%d"
    date_format_alternative_dd_mm_yyyy = "%d.%m.%Y"
    time_format = "%H:%M:%S"

    @staticmethod
    def get_format(format_number: int = 0) -> str:
        if format_number == 0:
            date_format = DateTimeFormats.date_format_iso_8601.value
        elif format_number == 1:
            date_format = DateTimeFormats.date_format_iso_8601_no_dash.value
        elif format_number == 2:
            date_format = DateTimeFormats.date_format_alternative_dd_mm_yyyy.value
        else:
            # Default for numbers outside supported range
            date_format = DateTimeFormats.date_format_iso_8601
            logger.warning(f"{DateTimeFormats.__class__}: {format_number} not supported, defaulted to 0 (ISO8601)")
        return f"{date_format} {DateTimeFormats.time_format.value}"


class DateUtils:
    """
    Utility class for handling date and time serialization and parsing.

    Methods:
        serialize(date: Any) -> Any:
            Serializes various types of date inputs into a standardized string format.

        parse(date_str: str) -> datetime | None:
            Parses a date string into a datetime object.

        is_date(value: Any) -> bool:
            Checks if a value is a valid date or date string.
    """

    @staticmethod
    def serialize(date: Any) -> Any:
        if isinstance(date, datetime):
            return date.strftime("%Y-%m-%d %H:%M:%S")
        elif isinstance(date, str):
            parsed_date = DateUtils.parse(date)
            if parsed_date:
                return parsed_date.strftime("%Y-%m-%d %H:%M:%S")
            else:
                logger.warning(f"Failed to parse date string: {date}")
                return date
        elif isinstance(date, list):
            return [DateUtils.serialize(item) for item in date]
        elif isinstance(date, dict):
            return {str(k): DateUtils.serialize(vv) for k, vv in date.items()}
        elif isinstance(date, BaseModel):
            return {str(k): DateUtils.serialize(getattr(date, k)) for k in date.model_fields}
        elif isinstance(date, TimeSeries):
            return {
                "periods": DateUtils.serialize(date.periods),
                "values": DateUtils.serialize(date.values),
                "unit": DateUtils.serialize(date.unit),
            }
        elif hasattr(date, "to_dict"):
            return DateUtils.serialize(date.to_dict())
        else:
            logger.warning(f"Unhandled data type: {type(date)}")
            return date

    @staticmethod
    def parse(date_str: str) -> datetime | None:
        try:
            return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        except ValueError as e:
            logger.error(f"Error parsing date string: {date_str} - {e}")
            return None

    @staticmethod
    def is_date(value: Any) -> bool:
        if isinstance(value, datetime):
            return True
        if isinstance(value, str):
            try:
                datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
                return True
            except ValueError:
                return False
        return False
