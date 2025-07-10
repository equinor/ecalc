import abc
from uuid import UUID

from libecalc.common.temporal_model import TemporalModel


class CategoryService(abc.ABC):
    @abc.abstractmethod
    def get_category(self, id: UUID) -> TemporalModel[str] | None: ...
