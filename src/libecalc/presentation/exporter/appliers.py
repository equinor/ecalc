import abc
from datetime import datetime
from typing import Any, Dict, Optional

from libecalc.application.graph_result import GraphResult
from libecalc.common.math.numbers import Numbers
from libecalc.common.time_utils import Frequency
from libecalc.common.units import Unit
from libecalc.presentation.exporter.configs import configs
from libecalc.presentation.exporter.dto.dtos import QueryResult
from libecalc.presentation.exporter.queries import Query


class Modifier(abc.ABC):
    def __init__(self, modifier: Optional["Modifier"] = None):
        """Modifiers can be chained, just make sure in/output of the modifiers are compatible.

        Modifier is completely private, to not be inherited by children
        :param modifier:
        """
        self.__modifier = modifier

    def modify(self, data: Dict[datetime, float]) -> Dict[datetime, Any]:
        """Public modify() method that is used in order to be able
        chain modifiers, if needed.
        :param data:
        :return:
        """
        if self.__modifier is not None:
            return self._modify(self.__modifier._modify(data))

        return self._modify(data)

    @abc.abstractmethod
    def _modify(self, data: Dict[datetime, float]) -> Dict[datetime, Any]:
        """Needs to be implemented by extending classes. Do NOT call
        super()'s methods, or the chained modifiers
        :param data:
        :return:
        """
        pass


class NullModifier(Modifier):
    """Default modifier, makes no changes, just pipes the data through."""

    def _modify(self, data: Dict[datetime, float]) -> Dict[datetime, float]:
        return data


class InvertValuesModifier(Modifier):
    """Turns negative values positives, or positive values negative."""

    def _modify(self, data: Dict[datetime, float]) -> Dict[datetime, float]:
        return {key: -1.0 * value if value != 0 else 0.0 for key, value in data.items()}


class FormatValuesToPrecisionModifier(Modifier):
    """Formats numbers according to LTP spec wrt significant numbers/decimals
    The current spec says 6 decimals.
    """

    def _modify(self, data: Dict[datetime, float]) -> Dict[datetime, str]:
        return {key: Numbers.format_to_precision(value, precision=configs.LTP_PRECISION) for key, value in data.items()}


class Applier:
    """Should we skip aggregators and generators and make the "query" etc handle that?"""

    name: str
    title: str
    unit: Unit
    query: Query

    def __init__(
        self, name: str, title: str, unit: Unit, query: Query, modifier: Modifier = FormatValuesToPrecisionModifier()
    ):
        """:param name:
        :param title:
        :param unit:
        :param query:
        """
        self.name = name
        self.title = title
        self.unit = unit
        self.query = query
        self.modifier = modifier

    def apply(
        self,
        installation_graph: GraphResult,
        frequency: Frequency,
    ) -> Optional[QueryResult]:
        values = self.query.query(installation_graph, self.unit, frequency)
        return (
            QueryResult(
                name=self.name,
                title=self.title,
                unit=self.unit,
                values=self.modifier.modify(values),
            )
            if values
            else None
        )
