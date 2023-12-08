from libecalc.core.consumers.base.result import ConsumerResult


class PumpResult(ConsumerResult):
    operational_head: float

    @property
    def models(self):
        return []
