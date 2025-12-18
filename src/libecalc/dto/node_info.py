from pydantic import BaseModel

from libecalc.common.component_info.component_level import ComponentLevel
from libecalc.common.component_type import ComponentType
from libecalc.domain.energy.energy_component import EnergyContainerID
from libecalc.dto.utils.validators import ComponentNameStr


class NodeInfo(BaseModel):
    id: EnergyContainerID
    name: ComponentNameStr
    component_type: ComponentType

    @property
    def component_level(self) -> ComponentLevel:
        if self.component_type == ComponentType.ASSET:
            return ComponentLevel.ASSET
        elif self.component_type == ComponentType.INSTALLATION:
            return ComponentLevel.INSTALLATION
        elif self.component_type == ComponentType.GENERATOR_SET:
            return ComponentLevel.GENERATOR_SET
        elif self.component_type in [
            ComponentType.COMPRESSOR_SYSTEM,
            ComponentType.PUMP_SYSTEM,
        ]:
            return ComponentLevel.SYSTEM
        else:
            return ComponentLevel.CONSUMER
