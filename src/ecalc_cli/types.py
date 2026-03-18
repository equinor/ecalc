import enum


class DateFormat(str, enum.Enum):
    """Supported date formats in ecalc CLI."""

    ISO_8601 = "0"
    """YYYY-MM-DD"""

    ISO_8601_NO_DASH = "1"
    """YYYYMMDD"""

    DD_MM_YYYY = "2"
    """DD_MM_YYYY"""


class Frequency(str, enum.Enum):
    NONE = "NONE"
    YEAR = "YEAR"
    MONTH = "MONTH"
    DAY = "DAY"
