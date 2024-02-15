from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Union

from pydantic import BaseModel, ConfigDict

from libecalc.common.string.string_utils import to_camel_case


class NodeType:
    """Supported Node types in FDE diagram"""

    GENERATOR = "generator"
    INSTALLATION = "installation"
    CABLE = "cable"
    COMPRESSOR = "compressor"
    COMPRESSOR_SYSTEM = "compressor-system"
    DIRECT = "direct"
    ENGINE = "engine"
    ENGINE_GENERATOR_SET = "engine-generator-set"
    INPUT_OUTPUT_NODE = "input-output-node"
    PUMP = "pump"
    PUMP_SYSTEM = "pump-system"
    TABULATED = "tabulated"
    TURBINE = "turbine"
    TURBINE_GENERATOR_SET = "turbine-generator-set"
    WIND_TURBINE = "wind-turbine"
    WIND_TURBINE_SYSTEM = "wind-turbine-system"


class FlowType:
    """Supported flow types in FDE diagram"""

    FUEL = "fuel-flow"
    EMISSION = "emission-flow"
    ELECTRICITY = "electricity-flow"


class FlowDiagram(BaseModel):
    """Pydantic class for flowdiagram of eCalc model"""

    id: str
    title: str
    nodes: List[Node]
    edges: List[Edge]
    flows: List[Flow]
    start_date: datetime
    end_date: datetime
    model_config = ConfigDict(alias_generator=to_camel_case, populate_by_name=True)


class Flow(BaseModel):
    """Pydantic class for connection between nodes in FDE diagram"""

    id: str
    label: str
    type: str
    model_config = ConfigDict(frozen=True)


class Edge(BaseModel):
    from_node: str
    to_node: str
    flow: str
    model_config = ConfigDict(frozen=True, alias_generator=to_camel_case, populate_by_name=True)


class Node(BaseModel):
    """Component in flowdiagram model, ex. a turbine or compressor"""

    id: str
    title: Optional[str] = None
    type: Optional[str] = None
    subdiagram: Optional[Union[FlowDiagram, List[FlowDiagram]]] = None
    model_config = ConfigDict(frozen=True)


FlowDiagram.update_forward_refs()
