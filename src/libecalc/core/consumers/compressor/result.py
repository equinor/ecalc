from libecalc.core.consumers.base.result import ConsumerResult
from libecalc.domain.stream_conditions import Rate


class CompressorResult(ConsumerResult):
    recirculation_loss: Rate
    rate_exceeds_maximum: bool  # Seems very specific, should we replace this and is_valid with failure flags?

    @property
    def models(self):
        return []
