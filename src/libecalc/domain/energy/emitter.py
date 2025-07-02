import abc
from typing import TypeVar

from libecalc.common.utils.rates import TimeSeriesStreamDayRate
from libecalc.domain.common.entity import Entity
from libecalc.domain.common.entity_id import ID
from libecalc.domain.energy.component_energy_context import ComponentEnergyContext
from libecalc.domain.energy.energy_model import EnergyModel

ID_T = TypeVar("ID_T", bound=ID)


class Emitter(abc.ABC, Entity[ID_T]):
    """
    Something that emits something.
    """

    @property
    @abc.abstractmethod
    def id(self) -> str: ...

    @abc.abstractmethod
    def evaluate_emissions(
        self,
        energy_context: ComponentEnergyContext,
        energy_model: EnergyModel,
    ) -> dict[str, TimeSeriesStreamDayRate] | None: ...
