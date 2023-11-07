from datetime import datetime, timedelta
from typing import Dict, Iterable, List, Set, Tuple, Union

from libecalc import dto
from libecalc.common.time_utils import Period, Periods
from libecalc.dto import (
    CompressorConsumerFunction,
    CompressorTrainSimplifiedWithKnownStages,
    ElectricEnergyUsageModel,
    FuelEnergyUsageModel,
    SingleSpeedCompressorTrain,
    VariableSpeedCompressorTrain,
    VariableSpeedCompressorTrainMultipleStreamsAndPressures,
)
from libecalc.dto.base import ComponentType
from libecalc.dto.models.compressor import CompressorWithTurbine
from libecalc.dto.types import ConsumerType
from libecalc.presentation.flow_diagram.fde_models import (
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


def _create_generator_set_node(generator_set: dto.GeneratorSet, installation: dto.Installation) -> Node:
    return Node(
        id=f"{installation.name}-generator-set-{generator_set.name}",
        title=generator_set.name,
        type=NodeType.GENERATOR,
    )


def _create_legacy_pump_system_diagram(
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
    periods = _get_periods(set(energy_usage_model.keys()), global_end_date)
    for period in periods:
        energy_usage_model_step = energy_usage_model[period.start]
        flow_diagrams.append(
            FlowDiagram(
                id=consumer_id,
                title=consumer_title,
                start_date=period.start,
                end_date=period.end,
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


def _create_legacy_compressor_system_diagram(
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
    periods = _get_periods(set(energy_usage_model.keys()), global_end_date)
    for period in periods:
        energy_usage_model_step = energy_usage_model[period.start]

        flow_diagrams.append(
            FlowDiagram(
                id=consumer_id,
                title=consumer_title,
                start_date=period.start,
                end_date=period.end,
                nodes=[
                    Node(
                        id=compressor.name,
                        title=compressor.name,
                        type=NodeType.COMPRESSOR,
                        subdiagram=FlowDiagram(
                            id=compressor.name,
                            title=compressor.name,
                            start_date=period.start,
                            end_date=period.end,
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


def _create_system_diagram(
    system: dto.components.ConsumerSystem,
    global_end_date: datetime,
) -> List[FlowDiagram]:
    timesteps = _get_timesteps(system.consumers)
    return [
        FlowDiagram(
            id=system.id,
            title=system.name,
            start_date=min(timesteps),
            end_date=max([*timesteps, global_end_date]),
            nodes=[
                Node(
                    id=consumer.name,
                    title=consumer.name,
                    type=NodeType.COMPRESSOR if consumer.component_type == ComponentType.COMPRESSOR else NodeType.PUMP,
                )
                for consumer in system.consumers
            ],
            edges=[],
            flows=[],
        )
    ]


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
    periods = _get_periods(set(energy_usage_model.keys()), global_end_date)
    compressor_train_step = list(energy_usage_model.values())[0].model
    return [
        FlowDiagram(
            id=node_id,
            title=title,
            start_date=period.start,
            end_date=period.end,
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
        for period in periods
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
    periods = _get_periods(set(energy_usage_model.keys()), global_end_date)
    for period in periods:
        compressor_train_type = list(energy_usage_model.values())[0].model.compressor_train

        if hasattr(compressor_train_type, "stages"):
            flow_diagrams.append(
                FlowDiagram(
                    id=node_id,
                    title=title,
                    start_date=period.start,
                    end_date=period.end,
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
    consumer: Union[dto.FuelConsumer, dto.ElectricityConsumer, dto.components.ConsumerSystem],
    installation_name: str,
    global_end_date: datetime,
) -> Node:
    node_id = f"{installation_name}-consumer-{consumer.name}"
    title = consumer.name
    if isinstance(consumer, (dto.FuelConsumer, dto.ElectricityConsumer)):
        component_type = list(consumer.energy_usage_model.values())[0].typ
        fde_type = _dto_model_type_to_fde_render_type_map.get(component_type, "default")
        if component_type == ConsumerType.PUMP_SYSTEM:
            subdiagram = _create_legacy_pump_system_diagram(
                consumer.energy_usage_model, node_id, title, global_end_date
            )
        elif component_type == ConsumerType.COMPRESSOR_SYSTEM:
            subdiagram = _create_legacy_compressor_system_diagram(
                consumer.energy_usage_model, node_id, title, global_end_date
            )
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
    elif isinstance(consumer, dto.components.ConsumerSystem):
        return Node(
            id=consumer.id,
            title=consumer.name,
            type=NodeType.PUMP_SYSTEM
            if consumer.consumers[0].component_type == ComponentType.PUMP
            else NodeType.COMPRESSOR_SYSTEM,
            subdiagram=_create_system_diagram(consumer, global_end_date=global_end_date),
        )
    else:
        raise ValueError(
            f"Unknown consumer of type '{getattr(consumer, 'component_type', 'unknown')}' with name '{getattr(consumer, 'name', 'unknown')}'"
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


def _get_timesteps(
    components: List[
        Union[
            dto.Asset,
            dto.Installation,
            dto.FuelConsumer,
            dto.GeneratorSet,
            dto.ElectricityConsumer,
            dto.components.PumpComponent,
            dto.components.CompressorComponent,
        ]
    ],
    shallow: bool = False,
) -> Set[datetime]:
    """
    Return a set of all timesteps for a component
    :param components:
    :param shallow: if we should get timesteps for consumers in a generator set or only for the generator set.
    Generator set is the only component that has dates in its own model and consumers with start dates.
    :return:
    """
    timesteps: Set[datetime] = set()
    for component in components:
        if isinstance(component, dto.Asset):
            timesteps = timesteps.union(_get_timesteps(component.installations, shallow=shallow))
        elif isinstance(component, dto.Installation):
            timesteps = timesteps.union(_get_timesteps(component.fuel_consumers, shallow=shallow))
        elif isinstance(component, dto.GeneratorSet):
            timesteps = timesteps.union(set(component.generator_set_model.keys()))
            if not shallow:
                timesteps = timesteps.union(_get_timesteps(component.consumers, shallow=shallow))
        elif isinstance(
            component,
            (
                dto.ElectricityConsumer,
                dto.FuelConsumer,
                dto.components.PumpComponent,
                dto.components.CompressorComponent,
            ),
        ):
            timesteps = timesteps.union(set(component.energy_usage_model.keys()))
        elif isinstance(component, dto.components.ConsumerSystem):
            timesteps = timesteps.union(_get_timesteps(component.consumers, shallow=shallow))
        else:
            raise ValueError(
                f"Unknown consumer of type '{getattr(component, 'component_type', 'unknown')}' with name '{getattr(component, 'name', 'unknown')}'"
            )
    return timesteps


def _consumer_is_active(
    consumer: Union[dto.FuelConsumer, dto.ElectricityConsumer, dto.GeneratorSet],
    period: Period,
) -> bool:
    """Check whether the consumer is active or not.
    :param consumer:
    :param period: the current period
    :return:
    """
    consumer_start_dates = _get_timesteps([consumer], shallow=True)
    consumer_start_date = sorted(consumer_start_dates)[0]
    return consumer_start_date < period.end


def _create_installation_flow_diagram(
    installation: dto.Installation,
    period: Period,
    global_end_date: datetime,
) -> FlowDiagram:
    generator_sets = [
        generator_set for generator_set in installation.fuel_consumers if isinstance(generator_set, dto.GeneratorSet)
    ]
    generator_set_nodes = []
    electricity_consumer_nodes = []
    generator_set_to_electricity_consumers = []
    for generator_set_dto in generator_sets:
        if _consumer_is_active(generator_set_dto, period):
            generator_set_node = _create_generator_set_node(
                generator_set_dto,
                installation,
            )
            generator_set_nodes.append(generator_set_node)

            for consumer in generator_set_dto.consumers:
                if _consumer_is_active(consumer, period):
                    electricity_consumer_node = _create_consumer_node(
                        consumer,
                        installation_name=installation.name,
                        global_end_date=global_end_date,
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
            installation_name=installation.name,
            global_end_date=global_end_date,
        )
        for fuel_consumer_dto in fuel_consumers_except_generator_sets
        if _consumer_is_active(fuel_consumer_dto, period)
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
        start_date=period.start,
        end_date=period.end,
        edges=[*fuel_to_fuel_consumer, *generator_set_to_electricity_consumers, *fuel_consumer_to_emission],
        nodes=[FUEL_NODE, *fuel_consumer_nodes, *electricity_consumer_nodes, EMISSION_NODE],
        flows=[FUEL_FLOW, ELECTRICITY_FLOW, EMISSIONS_FLOW],
    )


def _get_periods(
    start_dates: Iterable[datetime],
    global_end_date: datetime,
) -> Periods:
    start_dates = sorted(start_dates)
    return Periods.create_periods([*start_dates, global_end_date], include_before=False, include_after=False)


def _create_installation_fde(installation: dto.Installation, global_end_date: datetime) -> List[FlowDiagram]:
    """Create flow diagrams for each timestep including only the consumers relevant in that timestep
    :param installation:
    :return:
    """
    start_dates = _get_timesteps(installation.fuel_consumers)
    installation_periods = _get_periods(start_dates, global_end_date)
    installation_flow_diagrams = [
        _create_installation_flow_diagram(installation, installation_period, global_end_date)
        for installation_period in installation_periods
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


def _get_sorted_start_dates(ecalc_model: dto.Asset):
    return sorted(_get_timesteps([ecalc_model]))


def _get_global_dates(ecalc_model: dto.Asset, result_options: dto.ResultOptions) -> Tuple[datetime, datetime]:
    user_defined_start_date = result_options.start
    user_defined_end_date = result_options.end

    if user_defined_start_date is not None and user_defined_end_date is not None:
        return user_defined_start_date, user_defined_end_date

    start_dates = _get_sorted_start_dates(ecalc_model)
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
