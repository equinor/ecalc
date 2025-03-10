from datetime import datetime

from pydantic import BaseModel

from libecalc.common.version import Version


class RunInfo(BaseModel):
    """Data model for metadata about eCalc model runs."""

    version: Version
    start: datetime
    end: datetime | None = None

    def __str__(self):
        rstr = f"version '{str(self.version)}' started at '{self.start.strftime('%Y.%m.%d %H:%M:%S')}'"
        if self.end is not None:
            rstr += f" ended at '{self.end.strftime('%Y.%m.%d %H:%M:%S')}'"
        return rstr
