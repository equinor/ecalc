from datetime import datetime, timedelta
from typing import List, Protocol

from libecalc.common.graph import NodeID
from libecalc.common.time_utils import Period
from libecalc.presentation.flow_diagram.fde_models import FlowDiagram
from libecalc.presentation.yaml.domain.event import Event
from libecalc.presentation.yaml.model import YamlModel


class Node(Protocol):
    @property
    def events(self) -> List[Event]: ...


class EnergyFlowDiagram:
    def __init__(self, model: YamlModel, period: Period):
        self._model = model
        self._period = period

    @staticmethod
    def _get_global_period(events: List[Event], period: Period) -> Period:
        user_defined_start_date = period.start if period.start != datetime.min else None
        user_defined_end_date = period.end if period.end != datetime.max else None

        if user_defined_start_date is not None and user_defined_end_date is not None:
            return Period(start=user_defined_start_date, end=user_defined_end_date)

        start_dates = sorted(event.period.start for event in events)
        start_date = user_defined_start_date or start_dates[0]
        end_date = user_defined_end_date or start_dates[-1] + timedelta(days=365)
        return Period(start_date, end_date)

    def _process_node(self):
        pass

    def get_energy_flow_diagram(self, node_id: NodeID = None) -> FlowDiagram:
        graph = self._model.graph

        if node_id is None:
            node_id = graph.root

        node = graph.get_node(node_id)
        events = node.events

        global_period = self._get_global_period(events, self._period)
