import abc
from uuid import UUID

from libecalc.common.utils.rates import TimeSeriesRate, TimeSeriesStreamDayRate
from libecalc.domain.energy.component_energy_context import ComponentEnergyContext

EmissionName = str


class Emitter(abc.ABC):
    """
    Something that emits something.
    """

    @abc.abstractmethod
    def get_id(self) -> UUID: ...

    @abc.abstractmethod
    def evaluate_emissions(
        self,
        energy_context: ComponentEnergyContext,
    ) -> dict[str, TimeSeriesStreamDayRate] | None: ...

    @abc.abstractmethod
    def get_emissions(self) -> dict[EmissionName, TimeSeriesRate]: ...
