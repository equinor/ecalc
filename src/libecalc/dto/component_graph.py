from __future__ import annotations

import abc
from typing import Dict, List, Optional, Union

from libecalc.common.component_info.component_level import ComponentLevel
from libecalc.common.component_type import ComponentType
from libecalc.common.graph import Graph
from libecalc.common.time_utils import Period
from libecalc.common.utils.rates import TimeSeriesStreamDayRate
from libecalc.core.result import EcalcModelResult
from libecalc.core.result.emission import EmissionResult
from libecalc.dto.node_info import NodeInfo

ComponentID = str


class Component(abc.ABC):
    """
    Common info for a component in the model
    """

    @property
    @abc.abstractmethod
    def id(self) -> ComponentID: ...

    @property
    @abc.abstractmethod
    def name(self) -> str: ...

    @abc.abstractmethod
    def get_node_info(self) -> NodeInfo: ...

    @abc.abstractmethod
    def get_ecalc_model_result(self) -> Optional[EcalcModelResult]:
        """
        TODO: We should look into removing this generic result, as it does not makes sense to provide the same result for all types of components.
        """
        ...


class PowerProvider(Component, abc.ABC):
    """
    Provider that can deliver a power requirement
    """

    @abc.abstractmethod
    def provide_power(self, power_requirement: List[TimeSeriesStreamDayRate]): ...


class Emitter(Component, abc.ABC):
    """
    Something that causes emissions
    """

    @abc.abstractmethod
    def get_emissions(self, period: Period = None) -> Dict[str, EmissionResult]: ...


class PowerConsumer(Component, abc.ABC):
    """
    A consumer with a power requirement
    """

    @abc.abstractmethod
    def get_power_requirement(self, period: Period = None) -> TimeSeriesStreamDayRate: ...


class FuelConsumer(Emitter, abc.ABC):
    """
    An abstraction for provider and consumer that isn't able to give power requirement
    """

    @abc.abstractmethod
    def get_fuel_usage(self, period: Period = None) -> TimeSeriesStreamDayRate: ...


class ProcessGraph:
    """
    A set of components that should be evaluated together, but reported as separate components.
    """

    @abc.abstractmethod
    def get_components(self) -> List[Component]: ...

    @abc.abstractmethod
    def evaluate(self) -> None: ...


# TODO: Refactor ComponentGraph to EnergyGraph, protocol and composition instead of inherit from graph.
#       EnergyGraph should know about ProcessGraph.


class ComponentGraph(Graph[Union[Emitter, PowerConsumer, FuelConsumer, PowerProvider]]):
    def get_parent_installation_id(self, node_id: ComponentID) -> ComponentID:
        """
        Simple helper function to get the installation of any component with id

        Args:
            node_id:

        Returns:

        """

        # stop as soon as we get an installation. Ie. an installation of an installation, is itself...
        node_info = self.get_node_info(node_id)
        if node_info.component_level == ComponentLevel.INSTALLATION:
            return node_id

        parent_id = self.get_predecessor(node_id)
        return self.get_parent_installation_id(parent_id)

    def get_node_info(self, node_id: ComponentID) -> NodeInfo:
        node = self.nodes[node_id]
        return node.get_node_info()

    def get_node_id_by_name(self, name: str) -> ComponentID:
        for node in self.nodes.values():
            if node.name == name:
                return node.id

        raise ValueError(f"Component with name '{name}' not found in '{self.nodes[self.root].name}'")

    def get_nodes_of_type(self, component_type: ComponentType) -> List[ComponentID]:
        return [node.id for node in self.nodes.values() if node.get_node_info().component_type == component_type]
