from pydantic import ConfigDict

from libecalc.dto.base import EcalcBaseModel


class EnergyModel(EcalcBaseModel):
    """Generic/template/protocol. Only for sub classing, not direct use."""

    energy_usage_adjustment_constant: float
    energy_usage_adjustment_factor: float
    model_config = ConfigDict(use_enum_values=True)
