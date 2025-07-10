from uuid import UUID

from libecalc.common.component_type import ComponentType
from libecalc.common.utils.rates import TimeSeriesRate
from libecalc.common.variables import ExpressionEvaluator
from libecalc.domain.energy import Emitter, EnergyComponent
from libecalc.domain.hydrocarbon_export import HydrocarbonExport
from libecalc.domain.infrastructure.emitters.venting_emitter import VentingEmitter
from libecalc.domain.infrastructure.energy_components.fuel_consumer.fuel_consumer import FuelConsumerComponent
from libecalc.domain.infrastructure.energy_components.generator_set.generator_set_component import (
    GeneratorSetEnergyComponent,
)
from libecalc.domain.infrastructure.path_id import PathID
from libecalc.domain.installation import (
    ElectricityProducer,
    FuelConsumer,
    Installation,
    PowerConsumer,
    StorageContainer,
)
from libecalc.domain.regularity import Regularity
from libecalc.dto.component_graph import ComponentGraph


class PowerConsumerComponent(PowerConsumer):
    def __init__(self, producer_id: UUID | None, consumer_id: UUID, power_consumption: TimeSeriesRate):
        self._producer_id = producer_id
        self._consumer_id = consumer_id
        self._power_consumption = power_consumption

    def get_id(self) -> UUID:
        return self._consumer_id

    def get_producer_id(self) -> UUID | None:
        return self._producer_id

    def get_power_consumption(self) -> TimeSeriesRate:
        return self._power_consumption


class InstallationComponent(EnergyComponent, Installation):
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
        id: UUID,
        path_id: PathID,
        regularity: Regularity,
        hydrocarbon_export: HydrocarbonExport,
        fuel_consumers: list[GeneratorSetEnergyComponent | FuelConsumerComponent],
        expression_evaluator: ExpressionEvaluator,
        venting_emitters: list[VentingEmitter] | None = None,
    ):
        self._uuid = id
        self._path_id = path_id
        self.hydrocarbon_export = hydrocarbon_export
        self.regularity = regularity
        self.fuel_consumers = fuel_consumers
        self.expression_evaluator = expression_evaluator
        self.component_type = ComponentType.INSTALLATION

        self.evaluated_hydrocarbon_export_rate = self.hydrocarbon_export.time_series

        if venting_emitters is None:
            venting_emitters = []
        self.venting_emitters = venting_emitters

    def get_id(self) -> UUID:
        return self._uuid

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

    def get_electricity_producers(self) -> list[ElectricityProducer]:
        electricity_producers: list[ElectricityProducer] = []
        for fuel_consumer in self.fuel_consumers:
            if isinstance(fuel_consumer, ElectricityProducer):
                electricity_producers.append(fuel_consumer)

        return electricity_producers

    def get_storage_containers(self) -> list[StorageContainer]:
        storage_containers: list[StorageContainer] = []
        for venting_emitter in self.venting_emitters:
            if isinstance(venting_emitter, StorageContainer):
                storage_containers.append(venting_emitter)

        return storage_containers

    def get_fuel_consumers(self) -> list[FuelConsumer]:
        return self.fuel_consumers

    def get_power_consumers(self) -> list[PowerConsumer]:
        power_consumers: list[PowerConsumer] = []
        for fuel_consumer in self.fuel_consumers:
            if not isinstance(fuel_consumer, GeneratorSetEnergyComponent):
                continue

            for electricity_consumer in fuel_consumer.consumers:
                power_consumption = electricity_consumer.get_power_consumption()
                if power_consumption is None:
                    continue
                power_consumers.append(
                    PowerConsumerComponent(
                        producer_id=fuel_consumer.get_id(),
                        consumer_id=electricity_consumer.get_id(),
                        power_consumption=power_consumption,
                    )
                )

        for fuel_consumer in self.fuel_consumers:
            if not isinstance(fuel_consumer, FuelConsumerComponent):
                continue

            power_consumption = fuel_consumer.get_power_consumption()
            if power_consumption is None:
                continue

            power_consumers.append(
                PowerConsumerComponent(
                    producer_id=None,
                    consumer_id=fuel_consumer.get_id(),
                    power_consumption=power_consumption,
                )
            )
        return power_consumers

    def get_emitters(self) -> list[Emitter]:
        return [*self.fuel_consumers, *self.venting_emitters]
