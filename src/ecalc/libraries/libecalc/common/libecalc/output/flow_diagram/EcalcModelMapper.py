from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Iterable, List, Set, Tuple, Union

from libecalc import dto
from libecalc.dto import (
    CompressorConsumerFunction,
    CompressorTrainSimplifiedWithKnownStages,
    ElectricEnergyUsageModel,
    FuelEnergyUsageModel,
    SingleSpeedCompressorTrain,
    VariableSpeedCompressorTrain,
    VariableSpeedCompressorTrainMultipleStreamsAndPressures,
)
from libecalc.dto.models.compressor import CompressorWithTurbine
from libecalc.dto.types import ConsumerType
from libecalc.output.flow_diagram.fde_models import (
    Edge,
    Flow,
    FlowDiagram,
    FlowType,
    Node,
    NodeType,
)

FUEL_NODE = Node(id="fuel-input", title="Fuel", type=NodeType.INPUT_OUTPUT_NODE)
INPUT_NODE = Node(id="input", title="Input", type=NodeType.INPUT_OUTPUT_NODE)
EMISSION_NODE = Node(id="emission-output", title="Emission", type=NodeType.INPUT_OUTPUT_NODE)

FUEL_FLOW = Flow(id="fuel-flow", label="Fuel", type=FlowType.FUEL)
EMISSIONS_FLOW = Flow(id="emission-flow", label="Emissions", type=FlowType.EMISSION)
ELECTRICITY_FLOW = Flow(id="electricity-flow", label="Electricity", type=FlowType.ELECTRICITY)


@dataclass
class TimeInterval:
    start_date: datetime
    end_date: datetime

    def contains(self, date_check: datetime):
        return self.start_date <= date_check <= self.end_date


def _create_generator_set_node(generator_set: dto.GeneratorSet, installation: dto.Installation) -> Node:
    return Node(
        id=f"{installation.name}-generator-set-{generator_set.name}",
        title=generator_set.name,
        type=NodeType.GENERATOR,
    )


def _create_pump_system_diagram(
    energy_usage_model: Dict[datetime, dto.PumpSystemConsumerFunction],
    consumer_id: str,
    consumer_title: str,
    global_end_date: datetime,
) -> List[FlowDiagram]:
    """Create subchart for energy usage model
    :param energy_usage_model:
    :return: list of flow diagrams. List of flow diagrams as we always add a default date in dtos.
    """
    flow_diagrams = []
    time_intervals = _get_time_intervals(set(energy_usage_model.keys()), global_end_date)
    for time_interval in time_intervals:
        energy_usage_model_step = energy_usage_model[time_interval.start_date]
        flow_diagrams.append(
            FlowDiagram(
                id=consumer_id,
                title=consumer_title,
                start_date=time_interval.start_date,
                end_date=time_interval.end_date,
                nodes=[
                    Node(
                        id=pump.name,
                        title=pump.name,
                        type=NodeType.PUMP,
                    )
                    for pump in energy_usage_model_step.pumps
                ],
                edges=[],
                flows=[],
            )
        )
    return flow_diagrams


def _create_compressor_system_diagram(
    energy_usage_model: Dict[datetime, dto.CompressorSystemConsumerFunction],
    consumer_id: str,
    consumer_title: str,
    global_end_date: datetime,
) -> List[FlowDiagram]:
    """Create subchart for energy usage model
    :param energy_usage_model:
    :return: list of flow diagrams. List of flow diagrams as we always add a default date in dtos.
    """
    flow_diagrams = []
    time_intervals = _get_time_intervals(set(energy_usage_model.keys()), global_end_date)
    for time_interval in time_intervals:
        energy_usage_model_step = energy_usage_model[time_interval.start_date]

        flow_diagrams.append(
            FlowDiagram(
                id=consumer_id,
                title=consumer_title,
                start_date=time_interval.start_date,
                end_date=time_interval.end_date,
                nodes=[
                    Node(
                        id=compressor.name,
                        title=compressor.name,
                        type=NodeType.COMPRESSOR,
                        subdiagram=FlowDiagram(
                            id=compressor.name,
                            title=compressor.name,
                            start_date=time_interval.start_date,
                            end_date=time_interval.end_date,
                            nodes=[
                                Node(
                                    id=f"{compressor.name} stage {index}",
                                    title=f"{compressor.name} stage {index}",
                                    type=NodeType.COMPRESSOR,
                                )
                                for index in range(len(compressor.compressor_train.compressor_train.stages))
                            ],
                            edges=[],
                            flows=[],
                        )
                        if hasattr(compressor.compressor_train, "compressor_train")
                        else [],
                    )
                    for compressor in energy_usage_model_step.compressors
                ],
                edges=[],
                flows=[],
            )
        )
    return flow_diagrams


_dto_model_type_to_fde_render_type_map = {
    ConsumerType.DIRECT: NodeType.DIRECT,
    ConsumerType.PUMP_SYSTEM: NodeType.PUMP_SYSTEM,
    ConsumerType.COMPRESSOR_SYSTEM: NodeType.COMPRESSOR_SYSTEM,
    ConsumerType.COMPRESSOR: NodeType.COMPRESSOR,
    ConsumerType.PUMP: NodeType.PUMP,
    ConsumerType.TABULATED: NodeType.TABULATED,
}


def _create_compressor_train_diagram(
    energy_usage_model: Dict[datetime, dto.CompressorConsumerFunction],
    node_id: str,
    title: str,
    global_end_date: datetime,
):
    """Create subchart for energy usage model
    :param energy_usage_model:
    :return: list of flow diagrams. List of flow diagrams as we always add a default date in dtos.
    """
    time_intervals = _get_time_intervals(set(energy_usage_model.keys()), global_end_date)
    compressor_train_step = list(energy_usage_model.values())[0].model
    return [
        FlowDiagram(
            id=node_id,
            title=title,
            start_date=time_interval.start_date,
            end_date=time_interval.end_date,
            nodes=[
                Node(
                    id=f"{title} stage {index}",
                    title=f"{title} stage {index}",
                    type=NodeType.COMPRESSOR,
                )
                for index, chart in enumerate(compressor_train_step.stages)
            ],
            edges=[],
            flows=[],
        )
        for time_interval in time_intervals
        if hasattr(compressor_train_step, "stages")
    ]


def _create_compressor_with_turbine_stages_diagram(
    energy_usage_model: Dict[datetime, dto.CompressorConsumerFunction],
    node_id: str,
    title: str,
    global_end_date: datetime,
):
    """Create subchart for energy usage model
    :param energy_usage_model:
    :return: list of flow diagrams. List of flow diagrams as we always add a default date in dtos.
    """
    flow_diagrams = []
    time_intervals = _get_time_intervals(set(energy_usage_model.keys()), global_end_date)
    for time_interval in time_intervals:
        compressor_train_type = list(energy_usage_model.values())[0].model.compressor_train

        if hasattr(compressor_train_type, "stages"):
            flow_diagrams.append(
                FlowDiagram(
                    id=node_id,
                    title=title,
                    start_date=time_interval.start_date,
                    end_date=time_interval.end_date,
                    nodes=[
                        Node(
                            id=f"{title} stage {index}",
                            title=f"{title} stage {index}",
                            type=NodeType.COMPRESSOR,
                        )
                        for index, chart in enumerate(compressor_train_type.stages)
                    ],
                    edges=[],
                    flows=[],
                )
            )
    return flow_diagrams


def _is_compressor_with_turbine(
    temporal_energy_usage_model: Dict[datetime, dto.ConsumerFunction],
) -> bool:
    """Checking if compressor type is compressor with turbine.

    Note: this does not handle consumer systems with CompressorWithTurbine
    """
    for energy_usage_model in temporal_energy_usage_model.values():
        if isinstance(energy_usage_model, CompressorConsumerFunction):
            if isinstance(energy_usage_model.model, CompressorWithTurbine):
                return True
    return False


def _create_consumer_node(
    consumer: Union[dto.FuelConsumer, dto.ElectricityConsumer],
    installation: dto.Installation,
    global_end_date: datetime,
) -> Node:
    node_id = f"{installation.name}-consumer-{consumer.name}"  # Assuming names are unique across all consumers
    title = consumer.name
    # FIXME Assuming type does not change between dates
    consumer_type = list(consumer.energy_usage_model.values())[0].typ
    fde_type = _dto_model_type_to_fde_render_type_map.get(consumer_type, "default")
    if consumer_type == ConsumerType.PUMP_SYSTEM:
        subdiagram = _create_pump_system_diagram(consumer.energy_usage_model, node_id, title, global_end_date)
    elif consumer_type == ConsumerType.COMPRESSOR_SYSTEM:
        subdiagram = _create_compressor_system_diagram(consumer.energy_usage_model, node_id, title, global_end_date)
    elif _is_compressor_with_turbine(consumer.energy_usage_model):
        fde_type = NodeType.TURBINE
        subdiagram = _create_compressor_with_turbine_stages_diagram(
            consumer.energy_usage_model, node_id, title, global_end_date
        )
    elif _is_compressor_train(consumer.energy_usage_model):
        subdiagram = _create_compressor_train_diagram(consumer.energy_usage_model, node_id, title, global_end_date)
    else:
        subdiagram = None

    return Node(
        id=node_id,
        title=consumer.name,
        type=fde_type,
        subdiagram=subdiagram,
    )


def _is_compressor_train(
    energy_usage_models: Dict[
        datetime,
        Union[ElectricEnergyUsageModel, FuelEnergyUsageModel],
    ],
) -> bool:
    """Checking if compressor type is compressor train simplified with known stages."""
    for energy_usage_model in energy_usage_models.values():
        if isinstance(energy_usage_model, CompressorConsumerFunction) and isinstance(
            energy_usage_model.model,
            (
                CompressorTrainSimplifiedWithKnownStages,
                VariableSpeedCompressorTrain,
                SingleSpeedCompressorTrain,
                VariableSpeedCompressorTrainMultipleStreamsAndPressures,
            ),
        ):
            return True
    return False


def _get_timesteps(consumers: List[Union[dto.FuelConsumer, dto.GeneratorSet]]) -> Set[datetime]:
    """Return a set of all timesteps
    :param consumers:
    :return:
    """
    timesteps: Set[datetime] = set()
    for consumer in consumers:
        if isinstance(consumer, dto.GeneratorSet):
            fuel_consumer_start_dates = consumer.generator_set_model.keys()
        else:
            fuel_consumer_start_dates = consumer.energy_usage_model.keys()
        timesteps = timesteps.union(fuel_consumer_start_dates)
        if isinstance(consumer, dto.GeneratorSet):
            for electricity_consumer in consumer.consumers:
                electricity_consumer_start_dates = electricity_consumer.energy_usage_model.keys()
                timesteps = timesteps.union(electricity_consumer_start_dates)
    return timesteps


def _consumer_is_active(
    consumer: Union[dto.FuelConsumer, dto.ElectricityConsumer, dto.GeneratorSet],
    time_interval: TimeInterval,
) -> bool:
    """Check whether the consumer is active or not. We only need to check the start date of the consumer as there is no
    way to set an end date for a consumer. (At least if we assume the type of the consumer does not change)
    :param consumer:
    :param time_interval: the current time interval
    :return:
    """
    consumer_start_dates = (
        consumer.energy_usage_model if not isinstance(consumer, dto.GeneratorSet) else consumer.generator_set_model
    )
    consumer_start_date = sorted(consumer_start_dates)[0]
    return consumer_start_date < time_interval.end_date


def _create_installation_flow_diagram(
    installation: dto.Installation,
    time_interval: TimeInterval,
    global_end_date: datetime,
) -> FlowDiagram:
    generator_sets = [
        generator_set for generator_set in installation.fuel_consumers if isinstance(generator_set, dto.GeneratorSet)
    ]
    generator_set_nodes = []
    electricity_consumer_nodes = []
    generator_set_to_electricity_consumers = []
    for generator_set_dto in generator_sets:
        if _consumer_is_active(generator_set_dto, time_interval):
            generator_set_node = _create_generator_set_node(
                generator_set_dto,
                installation,
            )
            generator_set_nodes.append(generator_set_node)

            for consumer in generator_set_dto.consumers:
                if _consumer_is_active(consumer, time_interval):
                    electricity_consumer_node = _create_consumer_node(
                        consumer,
                        installation,
                        global_end_date,
                    )
                    electricity_consumer_nodes.append(electricity_consumer_node)
                    generator_set_to_electricity_consumers.append(
                        Edge(
                            from_node=generator_set_node.id,
                            to_node=electricity_consumer_node.id,
                            flow=ELECTRICITY_FLOW.id,
                        )
                    )

    fuel_consumers_except_generator_sets = [
        fuel_consumer
        for fuel_consumer in installation.fuel_consumers
        if not isinstance(fuel_consumer, dto.GeneratorSet)
    ]

    fuel_consumer_except_generator_set_nodes = [
        _create_consumer_node(
            fuel_consumer_dto,
            installation,
            global_end_date,
        )
        for fuel_consumer_dto in fuel_consumers_except_generator_sets
        if _consumer_is_active(fuel_consumer_dto, time_interval)
    ]

    fuel_consumer_nodes = [
        *generator_set_nodes,
        *fuel_consumer_except_generator_set_nodes,
    ]

    fuel_to_fuel_consumer = [
        Edge(
            from_node=FUEL_NODE.id,
            to_node=consumer.id,
            flow=FUEL_FLOW.id,
        )
        for consumer in fuel_consumer_nodes
    ]
    fuel_consumer_to_emission = [
        Edge(
            from_node=consumer.id,
            to_node=EMISSION_NODE.id,
            flow=EMISSIONS_FLOW.id,
        )
        for consumer in fuel_consumer_nodes
    ]

    return FlowDiagram(
        id=f"installation-{installation.name}",
        title=installation.name,
        start_date=time_interval.start_date,
        end_date=time_interval.end_date,
        edges=[*fuel_to_fuel_consumer, *generator_set_to_electricity_consumers, *fuel_consumer_to_emission],
        nodes=[FUEL_NODE, *fuel_consumer_nodes, *electricity_consumer_nodes, EMISSION_NODE],
        flows=[FUEL_FLOW, ELECTRICITY_FLOW, EMISSIONS_FLOW],
    )


def _get_time_intervals(
    start_dates: Iterable[datetime],
    global_end_date: datetime,
) -> List[TimeInterval]:
    start_dates = sorted(start_dates)
    # Shift start dates one and append an extra date at the end to ensure we always have a start and end date.
    end_dates = start_dates[1:] + [global_end_date]
    return [
        TimeInterval(
            start_date=start_date,
            end_date=end_date,
        )
        for start_date, end_date in zip(start_dates, end_dates)
    ]


def _create_installation_fde(installation: dto.Installation, global_end_date: datetime) -> List[FlowDiagram]:
    """Create flow diagrams for each timestep including only the consumers relevant in that timestep
    :param installation:
    :return:
    """
    start_dates = _get_timesteps(installation.fuel_consumers)
    installation_time_intervals = _get_time_intervals(start_dates, global_end_date)
    installation_flow_diagrams = [
        _create_installation_flow_diagram(installation, installation_time_interval, global_end_date)
        for installation_time_interval in installation_time_intervals
    ]

    if len(installation_flow_diagrams) <= 1:
        return installation_flow_diagrams

    return _filter_duplicate_flow_diagrams(installation_flow_diagrams)


def _filter_duplicate_flow_diagrams(installation_flow_diagrams: List[FlowDiagram]) -> List[FlowDiagram]:
    """We might create flow diagrams that are equal. When having several consumers with different dates,
    the user can change a property that isn't visible in the flow diagram.
    """
    filtered_flow_diagrams = [installation_flow_diagrams[0]]
    last_not_filtered_flow_diagram = installation_flow_diagrams[0]
    for index in range(1, len(installation_flow_diagrams)):
        current_fd = installation_flow_diagrams[index]
        is_visibly_equal = (
            last_not_filtered_flow_diagram.nodes == current_fd.nodes
            and last_not_filtered_flow_diagram.edges == current_fd.edges
            and last_not_filtered_flow_diagram.flows == current_fd.flows
        )
        if not is_visibly_equal:
            filtered_flow_diagrams.append(current_fd)
            last_not_filtered_flow_diagram = current_fd
        else:
            # Extend the time period for the flow-diagram that is not filtered if the current is a duplicate.
            last_not_filtered_flow_diagram.end_date = current_fd.end_date
    return filtered_flow_diagrams


def _create_installation_node(installation: dto.Installation, global_end_date: datetime) -> Node:
    return Node(
        id=f"installation-{installation.name}",
        title=installation.name,
        type=NodeType.INSTALLATION,
        subdiagram=_create_installation_fde(installation, global_end_date),
    )


def _get_start_dates(ecalc_model: dto.Asset):
    start_dates: Set[datetime] = set()
    for installation in ecalc_model.installations:
        start_dates = start_dates.union(_get_timesteps(installation.fuel_consumers))
    sorted_start_dates = sorted(start_dates)
    return sorted_start_dates


def _get_global_dates(ecalc_model: dto.Asset, result_options: dto.ResultOptions) -> Tuple[datetime, datetime]:
    user_defined_start_date = result_options.start
    user_defined_end_date = result_options.end

    if user_defined_start_date is not None and user_defined_end_date is not None:
        return user_defined_start_date, user_defined_end_date

    start_dates = _get_start_dates(ecalc_model)
    start_date = user_defined_start_date or start_dates[0]
    end_date = user_defined_end_date or start_dates[-1] + timedelta(days=365)
    return start_date, end_date


class EcalcModelMapper:
    @staticmethod
    def from_dto_to_fde(ecalc_model: dto.Asset, result_options: dto.ResultOptions) -> FlowDiagram:
        global_start_date, global_end_date = _get_global_dates(ecalc_model, result_options)
        installation_nodes = [
            _create_installation_node(installation, global_end_date) for installation in ecalc_model.installations
        ]

        edges = []
        for installation in installation_nodes:
            edges.append(
                Edge(
                    from_node=FUEL_NODE.id,
                    to_node=installation.id,
                    flow=FUEL_FLOW.id,
                )
            )
            edges.append(
                Edge(
                    from_node=installation.id,
                    to_node=EMISSION_NODE.id,
                    flow=EMISSIONS_FLOW.id,
                )
            )

        return FlowDiagram(
            id="area",
            title="Area",
            nodes=[FUEL_NODE, *installation_nodes, EMISSION_NODE],
            flows=[FUEL_FLOW, EMISSIONS_FLOW],
            edges=edges,
            start_date=global_start_date,
            end_date=global_end_date,
        )
