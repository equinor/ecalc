from datetime import datetime
from typing import Optional

try:
    from pydantic.v1 import BaseModel
except ImportError:
    from pydantic import BaseModel

from libecalc.common.version import Version


class RunInfo(BaseModel):
    """Data model for metadata about eCalc model runs."""

    version: Version
    start: datetime
    end: Optional[datetime] = None

    def __str__(self):
        rstr = f"version '{str(self.version)}' started at '{self.start.strftime('%Y.%m.%d %H:%M:%S')}'"
        if self.end is not None:
            rstr += f" ended at '{self.end.strftime('%Y.%m.%d %H:%M:%S')}'"
        return rstr
