from libecalc.common.time_utils import Period


class Event:
    def __init__(self, period: Period, name: str = None):
        self.period = period
        self.name = name
