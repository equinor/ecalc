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


class FlowDiagramBaseModel(BaseModel):
    """Pydantic basemodel for FDE pydantic models

    Needed for specifying datetime format in json dumps
    """

    # TODO[pydantic]: The following keys were deprecated: `json_encoders`.
    # Check https://docs.pydantic.dev/dev-v2/migration/#changes-to-config for more information.
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
    )


class FlowDiagram(FlowDiagramBaseModel):
    """Pydantic class for flowdiagram of eCalc model"""

    id: str
    title: str
    nodes: List[Node]
    edges: List[Edge]
    flows: List[Flow]
    start_date: datetime
    end_date: datetime
    model_config = ConfigDict(alias_generator=to_camel_case, populate_by_name=True)


class Flow(FlowDiagramBaseModel):
    """Pydantic class for connection between nodes in FDE diagram"""

    id: str
    label: str
    type: str
    model_config = ConfigDict(frozen=True)


class Edge(FlowDiagramBaseModel):
    from_node: str
    to_node: str
    flow: str
    model_config = ConfigDict(frozen=True, alias_generator=to_camel_case, populate_by_name=True)


class Node(FlowDiagramBaseModel):
    """Component in flowdiagram model, ex. a turbine or compressor"""

    id: str
    title: Optional[str] = None
    type: Optional[str] = None
    subdiagram: Optional[Union[FlowDiagram, List[FlowDiagram]]] = None
    model_config = ConfigDict(frozen=True)


FlowDiagram.update_forward_refs()
