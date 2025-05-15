from libecalc.common.component_type import ComponentType
from libecalc.common.variables import ExpressionEvaluator
from libecalc.domain.energy import EnergyComponent
from libecalc.domain.hydrocarbon_export import HydrocarbonExport
from libecalc.domain.infrastructure.emitters.venting_emitter import VentingEmitter
from libecalc.domain.infrastructure.energy_components.fuel_consumer.fuel_consumer import FuelConsumer
from libecalc.domain.infrastructure.energy_components.generator_set.generator_set_component import (
    GeneratorSetEnergyComponent,
)
from libecalc.domain.infrastructure.path_id import PathID
from libecalc.domain.regularity import Regularity
from libecalc.dto.component_graph import ComponentGraph
from libecalc.dto.types import InstallationUserDefinedCategoryType
from libecalc.dto.utils.validators import (
    convert_expression,
)


class Installation(EnergyComponent):
    """
    Represents an installation, serving as a container for energy components and emitters
    such as fuel consumers and venting emitters. This class facilitates the evaluation
    and validation of metrics like regularity and hydrocarbon export rates
    based on its defined temporal models.

    While the `Installation` class provides methods for evaluating operational metrics,
    its primary role is to act as a container and orchestrator for energy-related data
    across multiple components.
    """

    def __init__(
        self,
        path_id: PathID,
        regularity: Regularity,
        hydrocarbon_export: HydrocarbonExport,
        fuel_consumers: list[GeneratorSetEnergyComponent | FuelConsumer],
        expression_evaluator: ExpressionEvaluator,
        venting_emitters: list[VentingEmitter] | None = None,
        user_defined_category: InstallationUserDefinedCategoryType | None = None,
    ):
        self._path_id = path_id
        self.hydrocarbon_export = hydrocarbon_export
        self.regularity = regularity
        self.fuel_consumers = fuel_consumers
        self.expression_evaluator = expression_evaluator
        self.user_defined_category = user_defined_category
        self.component_type = ComponentType.INSTALLATION

        self.evaluated_hydrocarbon_export_rate = self.hydrocarbon_export.time_series

        if venting_emitters is None:
            venting_emitters = []
        self.venting_emitters = venting_emitters

    @property
    def name(self) -> str:
        return self._path_id.get_name()

    def is_fuel_consumer(self) -> bool:
        return True

    def is_electricity_consumer(self) -> bool:
        # Should maybe be True if power from shore?
        return False

    def is_provider(self) -> bool:
        return False

    def get_component_process_type(self) -> ComponentType:
        return self.component_type

    def get_name(self) -> str:
        return self._path_id.get_name()

    @property
    def id(self) -> str:
        return self._path_id.get_name()  # id here is energy component name which is a str and expects a unique name

    def convert_expression_installation(self, data):
        # Implement the conversion logic here
        return convert_expression(data)

    def get_graph(self) -> ComponentGraph:
        graph = ComponentGraph()
        graph.add_node(self)
        for component in [*self.fuel_consumers, *self.venting_emitters]:
            if hasattr(component, "get_graph"):
                graph.add_subgraph(component.get_graph())
            else:
                graph.add_node(component)

            graph.add_edge(self.id, component.id)

        return graph
