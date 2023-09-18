import enum

from libecalc.common import time_utils


class DateFormat(str, enum.Enum):
    """Supported date formats in ecalc CLI."""

    ISO_8601 = "0"
    """YYYY-MM-DD"""

    ISO_8601_NO_DASH = "1"
    """YYYYMMDD"""

    DD_MM_YYYY = "2"
    """DD_MM_YYYY"""


Frequency = enum.Enum("Frequency", {e.name: e.name for e in time_utils.Frequency})  # type: ignore
