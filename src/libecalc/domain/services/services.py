from libecalc.domain.venting_emitter import VentingEmitter
from libecalc.dto import Asset, Installation
from libecalc.dto.component_graph import ComponentGraph


class UpdateGraphVentingEmitter:
    @staticmethod
    def _update_installation_graph(installation: Installation, venting_emitter: VentingEmitter) -> ComponentGraph:
        graph = ComponentGraph()
        graph.add_node(installation)

        if hasattr(venting_emitter, "get_graph"):
            graph.add_subgraph(venting_emitter.get_graph())
        else:
            graph.add_node(venting_emitter)

        graph.add_edge(installation.id, venting_emitter.id)

        return graph

    def update_asset_graph(
        self, asset: Asset, installation: Installation, venting_emitter: VentingEmitter
    ) -> ComponentGraph:
        graph = ComponentGraph()
        graph.add_node(asset)

        graph.add_subgraph(self._update_installation_graph(installation=installation, venting_emitter=venting_emitter))
        graph.add_edge(asset.id, installation.id)

        return graph
