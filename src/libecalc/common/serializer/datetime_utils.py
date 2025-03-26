from datetime import datetime
from typing import Any

from libecalc.common.logger import logger
from libecalc.common.serializer.types import JSONSerializable


class DateTimeUtils:
    """
    Utility class for handling serialization and parsing of datetime objects.

    Supports individual datetime objects, strings, lists and dictionaries.
    Logs warnings when input cannot be parsed or is of unsupported type.
    """

    # Centralized list of allowed date formats – currently only one
    SUPPORTED_FORMATS = [
        "%Y-%m-%d %H:%M:%S",  # 2024-03-26 15:45:00
    ]

    @staticmethod
    def serialize_date(date: Any) -> JSONSerializable:
        # Datetime object → formatted string
        if isinstance(date, datetime):
            return date.strftime(DateTimeUtils.SUPPORTED_FORMATS[0])

        # Try parsing string to datetime
        if isinstance(date, str):
            parsed = DateTimeUtils.parse_date(date)
            if parsed:
                return parsed.strftime(DateTimeUtils.SUPPORTED_FORMATS[0])
            logger.warning(f"Failed to parse date string: {date}")
            return date

        # Recursive handling for lists
        if isinstance(date, list):
            return [DateTimeUtils.serialize_date(d) for d in date]

        # Recursive handling for dicts
        if isinstance(date, dict):
            return {str(k): DateTimeUtils.serialize_date(v) for k, v in date.items()}

        logger.warning(f"Unhandled date type: {type(date)}")
        return date

    @staticmethod
    def parse_date(date_str: str) -> datetime | None:
        # Attempt parsing with supported formats
        for fmt in DateTimeUtils.SUPPORTED_FORMATS:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        logger.error(f"Error parsing date string: '{date_str}' – no matching format")
        return None

    @staticmethod
    def is_date(value: Any) -> bool:
        # Check if value is a datetime or matches one of the supported formats
        if isinstance(value, datetime):
            return True
        if isinstance(value, str):
            for fmt in DateTimeUtils.SUPPORTED_FORMATS:
                try:
                    datetime.strptime(value, fmt)
                    return True
                except ValueError:
                    continue
        return False
