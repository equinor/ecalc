from typing import Protocol

from libecalc.presentation.yaml.domain.time_series import TimeSeries


class TimeSeriesProvider(Protocol):
    def get_time_series(self, time_series_id: str) -> TimeSeries: ...

    def get_time_series_references(self) -> list[str]: ...
