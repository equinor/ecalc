from libecalc.common.errors.exceptions import EcalcError


class TimeSeriesNotFound(EcalcError):
    def __init__(self, time_series_reference: str, message: str = None):
        if message is None:
            message = f"Unable to find time series with reference '{time_series_reference}'"

        super().__init__("Time series not found", message)
