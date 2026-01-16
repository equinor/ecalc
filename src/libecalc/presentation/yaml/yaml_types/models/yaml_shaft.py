from typing import Literal

from pydantic import Field

from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.models.model_reference import ModelName
from libecalc.presentation.yaml.yaml_types.models.yaml_enums import YamlModelType


class YamlShaft(YamlBase):
    """YAML model for defining a shaft with mechanical efficiency.

    A shaft represents the physical rotating component that connects a driver
    (turbine/motor) to compressor(s). Mechanical efficiency accounts for
    losses in bearings, gearbox, and couplings.

    Example YAML:
        MODELS:
          - NAME: main_shaft
            TYPE: SHAFT
            MECHANICAL_EFFICIENCY: 0.95  # 5% mechanical loss

    Attributes:
        name: Unique name to identify this shaft model.
        type: Must be SHAFT.
        mechanical_efficiency: Fraction of shaft power that becomes gas power.
            Required, no default. Constraint: 0 < η ≤ 1.
            Typical values: 0.93-0.97 depending on configuration.
    """

    name: ModelName = Field(
        ...,
        description="Name of the shaft model. See documentation for more information.",
        title="NAME",
    )
    type: Literal[YamlModelType.SHAFT] = Field(
        ...,
        description="Defines the type of model. Must be SHAFT.",
        title="TYPE",
    )
    mechanical_efficiency: float = Field(
        ...,  # Required, no default - user must specify
        description="Mechanical efficiency of the shaft. Accounts for losses in bearings, gearbox, and couplings. "
        "Must be in range (0, 1]. Typical values: ~0.97 for direct drive, ~0.95 with gearbox, ~0.93 for large gearbox/VSD.",
        gt=0.0,
        le=1.0,
        title="MECHANICAL_EFFICIENCY",
    )

    def to_dto(self):
        raise NotImplementedError
