from typing import assert_never

from libecalc.common.component_type import ComponentType
from libecalc.common.time_utils import Period
from libecalc.domain.energy import Emitter, EnergyModel
from libecalc.domain.energy.energy_component import EnergyContainerID
from libecalc.presentation.flow_diagram.flow_diagram_dtos import (
    Edge,
    Flow,
    FlowDiagram,
    FlowType,
    Node,
    NodeType,
)

FUEL_NODE = Node(id="fuel-input", title="Fuel", type=NodeType.INPUT_OUTPUT_NODE)
EMISSION_NODE = Node(id="emission-output", title="Emission", type=NodeType.INPUT_OUTPUT_NODE)

FUEL_FLOW = Flow(id="fuel-flow", label="Fuel", type=FlowType.FUEL)
EMISSIONS_FLOW = Flow(id="emission-flow", label="Emissions", type=FlowType.EMISSION)
ELECTRICITY_FLOW = Flow(id="electricity-flow", label="Electricity", type=FlowType.ELECTRICITY)


class EnergyModelFlowDiagram:
    def __init__(self, energy_model: EnergyModel, model_period: Period):
        self._energy_model = energy_model
        self._model_period = model_period

    @staticmethod
    def _get_node_type(component_type: ComponentType) -> NodeType:
        assert component_type != ComponentType.ASSET, "We don't use the asset node"
        match component_type:
            case ComponentType.INSTALLATION:
                return NodeType.INSTALLATION
            case ComponentType.PUMP:
                return NodeType.PUMP
            case ComponentType.COMPRESSOR:
                return NodeType.COMPRESSOR
            case ComponentType.COMPRESSOR_SYSTEM:
                return NodeType.COMPRESSOR_SYSTEM
            case ComponentType.PUMP_SYSTEM:
                return NodeType.PUMP_SYSTEM
            case ComponentType.GENERATOR_SET:
                return NodeType.GENERATOR
            case ComponentType.GENERIC:
                # TODO: handle tabular? Check model?
                return NodeType.DIRECT
            case ComponentType.VENTING_EMITTER:
                # TODO: Missing appropriate NodeType
                return NodeType.DIRECT
            case _:
                assert_never(component_type)

    def _is_fuel_consumer(self, container_id: EnergyContainerID) -> bool:
        energy_container = self._energy_model.get_energy_container(container_id)
        return energy_container.is_fuel_consumer()

    def _is_power_provider(self, container_id: EnergyContainerID) -> bool:
        energy_container = self._energy_model.get_energy_container(container_id)
        return energy_container.is_provider()

    def _is_emitter(self, container_id: EnergyContainerID) -> bool:
        energy_container = self._energy_model.get_energy_container(container_id)
        return isinstance(energy_container, Emitter)

    def _get_energy_component_fde(self, node_id: EnergyContainerID) -> list[FlowDiagram] | None:
        consumers = self._energy_model.get_consumers(node_id)

        if not consumers:
            return None

        nodes = [FUEL_NODE, EMISSION_NODE]
        edges = []
        for consumer_id in consumers:
            nodes.append(self._get_node(consumer_id, include_subdiagram=not self._is_power_provider(consumer_id)))

            if self._is_fuel_consumer(consumer_id):
                edges.append(self._get_edge(from_node=FUEL_NODE.id, to_node=str(consumer_id), flow=FUEL_FLOW.id))
                edges.append(
                    self._get_edge(from_node=str(consumer_id), to_node=EMISSION_NODE.id, flow=EMISSIONS_FLOW.id)
                )
            elif self._is_emitter(consumer_id):
                edges.append(
                    self._get_edge(from_node=str(consumer_id), to_node=EMISSION_NODE.id, flow=EMISSIONS_FLOW.id)
                )

            if self._is_power_provider(consumer_id):
                # Assuming provider provides electricity, and that consumers should be included in the same fde
                el_consumers = self._energy_model.get_consumers(consumer_id)
                for el_consumer_id in el_consumers:
                    nodes.append(self._get_node(el_consumer_id))
                    edges.append(
                        self._get_edge(
                            from_node=str(consumer_id), to_node=str(el_consumer_id), flow=ELECTRICITY_FLOW.id
                        )
                    )

        energy_container = self._energy_model.get_energy_container(node_id)

        return [
            FlowDiagram(
                id=str(node_id),
                title=energy_container.get_name(),
                start_date=self._model_period.start,
                end_date=self._model_period.end,
                nodes=nodes,
                edges=edges,
                flows=[
                    FUEL_FLOW,
                    EMISSIONS_FLOW,
                    ELECTRICITY_FLOW,
                ],
            )
        ]

    def _get_edge(self, from_node: str, to_node: str, flow: str):
        return Edge(
            from_node=from_node,
            to_node=to_node,
            flow=flow,
        )

    def _get_node(self, node_id: EnergyContainerID, include_subdiagram: bool = True) -> Node:
        energy_container = self._energy_model.get_energy_container(node_id)
        return Node(
            id=str(node_id),  # Node id and subdiagram id should match
            title=energy_container.get_name(),
            type=self._get_node_type(energy_container.get_component_process_type()).value,
            subdiagram=self._get_energy_component_fde(node_id) if include_subdiagram else None,
        )

    def get_energy_flow_diagram(self) -> FlowDiagram:
        energy_components = self._energy_model.get_energy_components()
        installations = [
            energy_component
            for energy_component in energy_components
            if self._energy_model.get_energy_container(energy_component).get_component_process_type()
            == ComponentType.INSTALLATION
        ]
        installation_nodes = [self._get_node(installation) for installation in installations]

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
            start_date=self._model_period.start,
            end_date=self._model_period.end,
        )
