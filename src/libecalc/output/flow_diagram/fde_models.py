from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Union

from libecalc.common.string_utils import to_camel_case
from pydantic import BaseModel


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


class FlowDiagramBaseModel(BaseModel):
    """Pydantic basemodel for FDE pydantic models

    Needed for specifying datetime format in json dumps
    """

    class Config:
        json_encoders = {
            datetime: lambda v: v.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }


class FlowDiagram(FlowDiagramBaseModel):
    """Pydantic class for flowdiagram of eCalc model"""

    id: str
    title: str
    nodes: List[Node]
    edges: List[Edge]
    flows: List[Flow]
    start_date: datetime
    end_date: datetime

    class Config:
        alias_generator = to_camel_case
        allow_population_by_field_name = True


class Flow(FlowDiagramBaseModel):
    """Pydantic class for connection between nodes in FDE diagram"""

    id: str
    label: str
    type: str

    class Config:
        frozen = True


class Edge(FlowDiagramBaseModel):
    from_node: str
    to_node: str
    flow: str

    class Config:
        frozen = True
        alias_generator = to_camel_case
        allow_population_by_field_name = True


class Node(FlowDiagramBaseModel):
    """Component in flowdiagram model, ex. a turbine or compressor"""

    id: str
    title: Optional[str] = None
    type: Optional[str] = None
    subdiagram: Optional[Union[FlowDiagram, List[FlowDiagram]]]

    class Config:
        frozen = True


FlowDiagram.update_forward_refs()
