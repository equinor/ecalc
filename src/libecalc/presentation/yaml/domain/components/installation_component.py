from typing import List

from libecalc.common.component_info.component_level import ComponentLevel
from libecalc.common.component_type import ComponentType
from libecalc.common.string.string_utils import generate_id
from libecalc.common.time_utils import Period, define_time_model_for_period
from libecalc.common.units import Unit
from libecalc.common.utils.rates import RateType, TimeSeriesFloat, TimeSeriesRate
from libecalc.common.variables import ExpressionEvaluator
from libecalc.dto.component_graph import Component, ComponentGraph
from libecalc.dto.components import Consumer
from libecalc.dto.node_info import NodeInfo
from libecalc.dto.utils.validators import convert_expression
from libecalc.presentation.yaml.domain.components.fuel_consumer_component import FuelConsumerComponent
from libecalc.presentation.yaml.domain.components.generator_set_component import GeneratorSetComponent
from libecalc.presentation.yaml.domain.components.venting_emitter_component import VentingEmitter
from libecalc.presentation.yaml.domain.reference_service import ReferenceService
from libecalc.presentation.yaml.mappers.component_mapper import GeneratorSetMapper, InstallationMapper
from libecalc.presentation.yaml.yaml_types.components.yaml_installation import YamlInstallation


class InstallationComponent:
    def __init__(
        self,
        yaml_installation: YamlInstallation,
        reference_service: ReferenceService,
        target_period: Period,
        expression_evaluator: ExpressionEvaluator,
    ):
        self._target_period = target_period
        self._expression_evaluator = expression_evaluator
        self._yaml_installation = yaml_installation
        self._dto_installation = InstallationMapper(
            references=reference_service, target_period=target_period
        ).from_yaml_to_dto(yaml_installation)

        self.__generator_set_mapper = GeneratorSetMapper(references=reference_service, target_period=target_period)
        fuel_data = yaml_installation.fuel
        regularity = define_time_model_for_period(
            convert_expression(yaml_installation.regularity or 1), target_period=target_period
        )

        self._generator_sets = [
            GeneratorSetComponent(
                yaml_generator_set=generator_set,
                reference_service=reference_service,
                target_period=target_period,
                regularity=regularity,
                default_fuel_reference=fuel_data,
                expression_evaluator=expression_evaluator,
            )
            for generator_set in yaml_installation.generator_sets or []
        ]
        self._fuel_consumers: List[Consumer] = [
            FuelConsumerComponent(
                yaml_fuel_consumer=fuel_consumer,
                reference_service=reference_service,
                target_period=target_period,
                regularity=regularity,
                default_fuel_reference=fuel_data,
                expression_evaluator=expression_evaluator,
            )
            for fuel_consumer in yaml_installation.fuel_consumers or []
        ]

        self._venting_emitters: List[VentingEmitter] = [
            VentingEmitter(
                yaml_venting_emitter=venting_emitter,
                regularity=regularity,
                expression_evaluator=expression_evaluator,
            )
            for venting_emitter in yaml_installation.venting_emitters or []
        ]

    @property
    def id(self) -> str:
        return generate_id(self._yaml_installation.name)

    def get_graph(self) -> ComponentGraph:
        graph = ComponentGraph()
        graph.add_node(self)
        for component in self._fuel_consumers:
            if hasattr(component, "get_graph"):
                graph.add_subgraph(component.get_graph())
            else:
                graph.add_node(component)

            graph.add_edge(self.id, component.id)

        for component in self._generator_sets:
            if hasattr(component, "get_graph"):
                graph.add_subgraph(component.get_graph())
            else:
                graph.add_node(component)

            graph.add_edge(self.id, component.id)

        for component in self._venting_emitters:
            if hasattr(component, "get_graph"):
                graph.add_subgraph(component.get_graph())
            else:
                graph.add_node(component)

            graph.add_edge(self.id, component.id)

        return graph

    @property
    def name(self) -> str:
        return self._yaml_installation.name

    @property
    def regularity(self) -> TimeSeriesFloat:
        return TimeSeriesFloat(
            timesteps=self._expression_evaluator.get_time_vector(),
            values=self._expression_evaluator.evaluate(convert_expression(self._yaml_installation.regularity)).tolist(),
            unit=Unit.NONE,
        )

    @property
    def hydrocarbon_export_rate(self) -> TimeSeriesRate:
        return TimeSeriesRate(
            timesteps=self._expression_evaluator.get_time_vector(),
            values=self._expression_evaluator.evaluate(
                convert_expression(self._yaml_installation.hydrocarbon_export)
            ).tolist(),
            unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
            rate_type=RateType.CALENDAR_DAY,
            regularity=self.regularity.values,
        )

    def get_node_info(self) -> NodeInfo:
        return NodeInfo(
            id=self.id,
            name=self.name,
            component_level=ComponentLevel.INSTALLATION,
            component_type=ComponentType.INSTALLATION,
        )

    @property
    def venting_emitters(self) -> List[Component]:
        return self._venting_emitters

    @property
    def fuel_consumers(self):
        return
