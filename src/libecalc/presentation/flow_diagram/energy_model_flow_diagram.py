from typing import assert_never

from libecalc.common.component_type import ComponentType
from libecalc.common.time_utils import Period
from libecalc.domain.energy import Emitter, EnergyComponent, EnergyModel
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

    def _get_node_type(self, energy_component: EnergyComponent) -> NodeType:
        component_type = energy_component.get_component_process_type()
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

    def _get_energy_component_fde(self, energy_component: EnergyComponent) -> list[FlowDiagram] | None:
        consumers = self._energy_model.get_consumers(energy_component.id)

        if not consumers:
            return None

        nodes = [FUEL_NODE, EMISSION_NODE]
        edges = []
        for consumer in consumers:
            nodes.append(self._get_node(consumer, include_subdiagram=not consumer.is_provider()))

            if consumer.is_fuel_consumer():
                edges.append(self._get_edge(from_node=FUEL_NODE.id, to_node=consumer.id, flow=FUEL_FLOW.id))
                edges.append(self._get_edge(from_node=consumer.id, to_node=EMISSION_NODE.id, flow=EMISSIONS_FLOW.id))
            elif isinstance(consumer, Emitter):
                edges.append(self._get_edge(from_node=consumer.id, to_node=EMISSION_NODE.id, flow=EMISSIONS_FLOW.id))

            if consumer.is_provider():
                # Assuming provider provides electricity, and that consumers should be included in the same fde
                el_consumers = self._energy_model.get_consumers(consumer.id)
                for el_consumer in el_consumers:
                    nodes.append(self._get_node(el_consumer))
                    edges.append(
                        self._get_edge(from_node=consumer.id, to_node=el_consumer.id, flow=ELECTRICITY_FLOW.id)
                    )

        return [
            FlowDiagram(
                id=energy_component.id,
                title=energy_component.get_name(),
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

    def _get_node(self, energy_component: EnergyComponent, include_subdiagram: bool = True) -> Node:
        return Node(
            id=energy_component.id,  # Node id and subdiagram id should match
            title=energy_component.get_name(),
            type=self._get_node_type(energy_component).value,
            subdiagram=self._get_energy_component_fde(energy_component) if include_subdiagram else None,
        )

    def get_energy_flow_diagram(self) -> FlowDiagram:
        energy_components = self._energy_model.get_energy_components()
        installations = [
            energy_component
            for energy_component in energy_components
            if energy_component.get_component_process_type() == ComponentType.INSTALLATION
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
