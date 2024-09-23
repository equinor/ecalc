from pydantic import BaseModel

from libecalc.common.component_info.component_level import ComponentLevel
from libecalc.common.component_type import ComponentType
from libecalc.dto.utils.validators import ComponentNameStr


class NodeInfo(BaseModel):
    id: str
    name: ComponentNameStr
    component_level: ComponentLevel
    component_type: ComponentType
