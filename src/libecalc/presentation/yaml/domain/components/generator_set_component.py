import operator
from datetime import datetime
from functools import reduce
from typing import Dict, List, Optional

import numpy as np

from libecalc.common.component_info.component_level import ComponentLevel
from libecalc.common.component_type import ComponentType
from libecalc.common.errors.exceptions import ProgrammingError
from libecalc.common.graph import NodeID
from libecalc.common.string.string_utils import generate_id
from libecalc.common.temporal_model import TemporalModel
from libecalc.common.time_utils import Period
from libecalc.common.units import Unit
from libecalc.common.utils.rates import TimeSeriesStreamDayRate
from libecalc.common.variables import ExpressionEvaluator
from libecalc.core.consumers.generator_set import Genset
from libecalc.core.models.fuel import FuelModel
from libecalc.core.models.generator import GeneratorModelSampled
from libecalc.core.result import EcalcModelResult
from libecalc.core.result.emission import EmissionResult
from libecalc.dto.component_graph import ComponentGraph, Emitter, PowerProvider
from libecalc.dto.node_info import NodeInfo
from libecalc.expression import Expression
from libecalc.presentation.yaml.domain.components.electricity_consumer_component import ElectricityConsumerComponent
from libecalc.presentation.yaml.domain.reference_service import ReferenceService
from libecalc.presentation.yaml.mappers.component_mapper import GeneratorSetMapper
from libecalc.presentation.yaml.yaml_types.components.yaml_generator_set import YamlGeneratorSet


class GeneratorSetComponent(PowerProvider, Emitter):
    def __init__(
        self,
        yaml_generator_set: YamlGeneratorSet,
        reference_service: ReferenceService,
        target_period: Period,
        regularity: Dict[datetime, Expression],
        default_fuel_reference: Optional[str],
        expression_evaluator: ExpressionEvaluator,
    ):
        self._expression_evaluator = expression_evaluator
        self._yaml_generator_set = yaml_generator_set
        generator_set_mapper = GeneratorSetMapper(references=reference_service, target_period=target_period)
        self._dto_generator_set = generator_set_mapper.from_yaml_to_dto(
            yaml_generator_set,
            regularity=regularity,
            default_fuel=default_fuel_reference,
        )
        self._core_generator_set = Genset(
            id=self.id,
            name=self.name,
            temporal_generator_set_model=TemporalModel(
                {
                    start_time: GeneratorModelSampled(
                        fuel_values=model.fuel_values,
                        power_values=model.power_values,
                        energy_usage_adjustment_constant=model.energy_usage_adjustment_constant,
                        energy_usage_adjustment_factor=model.energy_usage_adjustment_factor,
                    )
                    for start_time, model in self._dto_generator_set.generator_set_model.items()
                }
            ),
        )

        self._electricity_consumers = [
            ElectricityConsumerComponent(
                electricity_consumer,
                reference_service=reference_service,
                target_period=target_period,
                regularity=regularity,
                default_fuel_reference=default_fuel_reference,
                expression_evaluator=expression_evaluator,
            )
            for electricity_consumer in self._yaml_generator_set.consumers
        ]

        self._ecalc_model_result: Optional[EcalcModelResult] = None
        self._emissions: Optional[Dict[str, EmissionResult]] = None

    @property
    def id(self) -> NodeID:
        return generate_id(self.name)

    @property
    def name(self) -> str:
        return self._yaml_generator_set.name

    def get_graph(self) -> ComponentGraph:
        graph = ComponentGraph()
        graph.add_node(self)
        for electricity_consumer in self._electricity_consumers:
            if hasattr(electricity_consumer, "get_graph"):
                graph.add_subgraph(electricity_consumer.get_graph())
            else:
                graph.add_node(electricity_consumer)

            graph.add_edge(self.id, electricity_consumer.id)

        return graph

    def get_node_info(self) -> NodeInfo:
        return NodeInfo(
            id=self.id,
            name=self.name,
            component_level=ComponentLevel.GENERATOR_SET,
            component_type=ComponentType.GENERATOR_SET,
        )

    def get_emissions(self, period: Period = None) -> Optional[Dict[str, EmissionResult]]:
        fuel_model = FuelModel(self._dto_generator_set.fuel)
        energy_usage = self.get_ecalc_model_result().component_result.energy_usage
        self._emissions = fuel_model.evaluate_emissions(
            expression_evaluator=self._expression_evaluator,
            fuel_rate=np.asarray(energy_usage.values),
        )
        return self._emissions

    def provide_power(self, power_requirement: List[TimeSeriesStreamDayRate], period: Period = None):
        number_of_periods = len(self._expression_evaluator.get_time_vector())

        aggregated_power_requirement = reduce(
            operator.add,
            power_requirement,
            TimeSeriesStreamDayRate(
                values=[0.0] * number_of_periods,
                timesteps=self._expression_evaluator.get_time_vector(),
                unit=Unit.MEGA_WATT,
            ),  # Initial value, handle no power output from components
        )

        self._ecalc_model_result = EcalcModelResult(
            component_result=self._core_generator_set.evaluate(
                expression_evaluator=self._expression_evaluator,
                power_requirement=np.asarray(aggregated_power_requirement.values),
            ),
            models=[],
            sub_components=[],
        )

    def get_ecalc_model_result(self) -> EcalcModelResult:
        if self._ecalc_model_result is None:
            raise ProgrammingError("Provide power first")

        return self._ecalc_model_result
