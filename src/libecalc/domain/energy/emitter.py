import abc
from uuid import UUID

from libecalc.common.utils.rates import TimeSeriesRate

EmissionName = str


class Emitter(abc.ABC):
    """
    Something that emits something.
    """

    @abc.abstractmethod
    def get_id(self) -> UUID: ...

    @abc.abstractmethod
    def get_emissions(self) -> dict[EmissionName, TimeSeriesRate]: ...
