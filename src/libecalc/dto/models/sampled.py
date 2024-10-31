from libecalc.dto.models.base import EnergyModel


class EnergyModelSampled(EnergyModel):
    headers: list[str]
    data: list[list[float]]
    # TODO: validate number of headers equals number of vectors
    # validate all vectors (in data) have equal length
