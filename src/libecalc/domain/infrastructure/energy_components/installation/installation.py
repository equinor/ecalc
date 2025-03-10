from libecalc.common.component_type import ComponentType
from libecalc.common.string.string_utils import generate_id
from libecalc.common.time_utils import Period
from libecalc.common.variables import ExpressionEvaluator
from libecalc.domain.energy import EnergyComponent
from libecalc.domain.infrastructure.emitters.venting_emitter import VentingEmitter
from libecalc.domain.infrastructure.energy_components.fuel_consumer.fuel_consumer import FuelConsumer
from libecalc.domain.infrastructure.energy_components.generator_set.generator_set_dto import GeneratorSet
from libecalc.dto.component_graph import ComponentGraph
from libecalc.dto.types import InstallationUserDefinedCategoryType
from libecalc.dto.utils.validators import (
    convert_expression,
    validate_temporal_model,
)
from libecalc.expression import Expression


class Installation(EnergyComponent):
    def __init__(
        self,
        name: str,
        regularity: dict[Period, Expression],
        hydrocarbon_export: dict[Period, Expression],
        fuel_consumers: list[GeneratorSet | FuelConsumer],
        expression_evaluator: ExpressionEvaluator,
        venting_emitters: list[VentingEmitter] | None = None,
        user_defined_category: InstallationUserDefinedCategoryType | None = None,
    ):
        self.name = name
        self.hydrocarbon_export = self.convert_expression_installation(hydrocarbon_export)
        self.regularity = self.convert_expression_installation(regularity)
        self.fuel_consumers = fuel_consumers
        self.expression_evaluator = expression_evaluator
        self.user_defined_category = user_defined_category
        self.component_type = ComponentType.INSTALLATION
        self.validate_installation_temporal_model()

        if venting_emitters is None:
            venting_emitters = []
        self.venting_emitters = venting_emitters

    def is_fuel_consumer(self) -> bool:
        return True

    def is_electricity_consumer(self) -> bool:
        # Should maybe be True if power from shore?
        return False

    def is_provider(self) -> bool:
        return False

    def is_container(self) -> bool:
        return True

    def get_component_process_type(self) -> ComponentType:
        return self.component_type

    def get_name(self) -> str:
        return self.name

    @property
    def id(self) -> str:
        return generate_id(self.name)

    def validate_installation_temporal_model(self):
        return validate_temporal_model(self.hydrocarbon_export)

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
