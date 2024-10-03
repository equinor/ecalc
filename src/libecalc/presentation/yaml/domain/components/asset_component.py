from typing import List

from libecalc.common.component_info.component_level import ComponentLevel
from libecalc.common.component_type import ComponentType
from libecalc.common.time_utils import Period
from libecalc.common.variables import ExpressionEvaluator
from libecalc.dto.component_graph import ComponentGraph
from libecalc.dto.node_info import NodeInfo
from libecalc.presentation.yaml.domain.components.installation_component import InstallationComponent
from libecalc.presentation.yaml.domain.reference_service import ReferenceService
from libecalc.presentation.yaml.yaml_models.yaml_model import YamlValidator


class AssetComponent:
    def __init__(
        self,
        yaml_asset: YamlValidator,
        reference_service: ReferenceService,
        target_period: Period,
        expression_evaluator: ExpressionEvaluator,
    ):
        self._yaml_asset = yaml_asset
        self._installations = [
            InstallationComponent(
                installation,
                reference_service=reference_service,
                target_period=target_period,
                expression_evaluator=expression_evaluator,
            )
            for installation in yaml_asset.installations
        ]

    @property
    def id(self) -> str:
        return self._yaml_asset.name

    def get_graph(self) -> ComponentGraph:
        graph = ComponentGraph()
        graph.add_node(self)
        for installation in self._installations:
            graph.add_subgraph(installation.get_graph())
            graph.add_edge(self.id, installation.id)

        return graph

    @property
    def name(self) -> str:
        return self._yaml_asset.name

    def get_node_info(self) -> NodeInfo:
        return NodeInfo(
            id=self.id,
            name=self.name,
            component_level=ComponentLevel.ASSET,
            component_type=ComponentType.ASSET,
        )

    @property
    def installations(self) -> List[InstallationComponent]:
        return self._installations
