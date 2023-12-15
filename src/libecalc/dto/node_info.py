try:
    from pydantic.v1 import BaseModel
except ImportError:
    from pydantic import BaseModel

from libecalc.common.component_info.component_level import ComponentLevel
from libecalc.dto.base import ComponentType
from libecalc.dto.utils.validators import ComponentNameStr


class NodeInfo(BaseModel):
    id: str
    name: ComponentNameStr
    component_level: ComponentLevel
    component_type: ComponentType
