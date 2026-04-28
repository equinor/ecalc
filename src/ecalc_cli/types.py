import enum


class DateFormat(enum.StrEnum):
    """Supported date formats in ecalc CLI."""

    ISO_8601 = "0"
    """YYYY-MM-DD"""

    ISO_8601_NO_DASH = "1"
    """YYYYMMDD"""

    DD_MM_YYYY = "2"
    """DD_MM_YYYY"""


class Frequency(enum.StrEnum):
    NONE = "NONE"
    YEAR = "YEAR"
    MONTH = "MONTH"
    DAY = "DAY"
