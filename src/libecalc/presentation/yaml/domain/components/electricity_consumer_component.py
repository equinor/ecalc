from datetime import datetime
from typing import Dict, Optional

from typing_extensions import deprecated

from libecalc.common.component_info.component_level import ComponentLevel
from libecalc.common.component_type import ComponentType
from libecalc.common.consumption_type import ConsumptionType
from libecalc.common.errors.exceptions import ProgrammingError
from libecalc.common.graph import NodeID
from libecalc.common.string.string_utils import generate_id
from libecalc.common.temporal_model import TemporalModel
from libecalc.common.time_utils import Period
from libecalc.common.utils.rates import TimeSeriesStreamDayRate
from libecalc.common.variables import ExpressionEvaluator
from libecalc.core.consumers.legacy_consumer.component import Consumer
from libecalc.core.consumers.legacy_consumer.consumer_function_mapper import EnergyModelMapper
from libecalc.core.result import EcalcModelResult
from libecalc.core.result.emission import EmissionResult
from libecalc.dto import ElectricEnergyUsageModel, ElectricityConsumer
from libecalc.dto.component_graph import PowerConsumer
from libecalc.dto.node_info import NodeInfo
from libecalc.expression import Expression
from libecalc.presentation.yaml.domain.reference_service import ReferenceService
from libecalc.presentation.yaml.mappers.component_mapper import ConsumerMapper
from libecalc.presentation.yaml.yaml_types.components.legacy.yaml_electricity_consumer import YamlElectricityConsumer


class ElectricityConsumerComponent(PowerConsumer):
    def __init__(
        self,
        yaml_fuel_consumer: YamlElectricityConsumer,
        reference_service: ReferenceService,
        target_period: Period,
        regularity: Dict[datetime, Expression],
        default_fuel_reference: Optional[str],
        expression_evaluator: ExpressionEvaluator,
    ):
        self._expression_evaluator = expression_evaluator
        self._yaml_consumer = yaml_fuel_consumer
        consumer_mapper = ConsumerMapper(references=reference_service, target_period=target_period)
        self._dto_consumer: ElectricityConsumer = consumer_mapper.from_yaml_to_dto(
            yaml_fuel_consumer,
            regularity=regularity,
            consumes=ConsumptionType.ELECTRICITY,
            default_fuel=default_fuel_reference,
        )
        self._core_consumer = Consumer(
            id=self.id,
            name=self.name,
            component_type=self.get_node_info().component_type,
            regularity=TemporalModel(self._dto_consumer.regularity),
            consumes=ConsumptionType.ELECTRICITY,
            energy_usage_model=TemporalModel(
                {
                    start_time: EnergyModelMapper.from_dto_to_domain(model)
                    for start_time, model in self._dto_consumer.energy_usage_model.items()
                }
            ),
        )

        # Keep results when calculated
        self._ecalc_model_result: Optional[EcalcModelResult] = None
        self._emissions: Optional[Dict[str, EmissionResult]] = None

    @property
    def id(self) -> NodeID:
        return generate_id(self._yaml_consumer.name)

    @property
    def name(self) -> str:
        return self._yaml_consumer.name

    def get_node_info(self) -> NodeInfo:
        return NodeInfo(
            id=self.id,
            name=self.name,
            component_level=ComponentLevel.CONSUMER
            if self._dto_consumer.component_type not in [ComponentType.COMPRESSOR_SYSTEM, ComponentType.PUMP_SYSTEM]
            else ComponentLevel.SYSTEM,
            component_type=self._dto_consumer.component_type,
        )

    def get_power_requirement(self, period: Period = None) -> TimeSeriesStreamDayRate:
        consumer_result = self._core_consumer.evaluate(self._expression_evaluator)
        self._ecalc_model_result = consumer_result
        return consumer_result.component_result.power

    def get_ecalc_model_result(self) -> EcalcModelResult:
        if self._ecalc_model_result is None:
            raise ProgrammingError("Propagate streams first")

        return self._ecalc_model_result

    @property
    @deprecated("We don't want to expose the dto directly, instead implement an interface with behaviour")
    def energy_usage_model(self) -> Dict[datetime, ElectricEnergyUsageModel]:
        return self._dto_consumer.energy_usage_model
