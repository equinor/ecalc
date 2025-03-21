from enum import Enum

from libecalc.common.logger import logger


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
