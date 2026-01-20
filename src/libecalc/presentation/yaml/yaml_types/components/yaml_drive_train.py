import enum
from typing import Literal

from pydantic import ConfigDict, Field

from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.components.yaml_expression_type import YamlExpressionType
from libecalc.presentation.yaml.yaml_types.yaml_temporal_model import YamlTemporalModel


class YamlDriveTrainType(str, enum.Enum):
    ELECTRICAL_DRIVE_TRAIN = "ELECTRICAL_DRIVE_TRAIN"
    TURBINE_DRIVE_TRAIN = "TURBINE_DRIVE_TRAIN"


class YamlCable(YamlBase):
    power_supply_reference: str
    cable_loss: YamlExpressionType


class YamlElectricalDriveTrain(YamlBase):
    model_config = ConfigDict(title="ElectricalDriveTrain")

    type: Literal[YamlDriveTrainType.ELECTRICAL_DRIVE_TRAIN] = Field(
        ...,
        description="Defines the type of drive train. See documentation for more information.",
        title="TYPE",
    )
    name: str

    power_supply_connection: YamlCable
    mechanical_efficiency: YamlExpressionType


class YamlTurbineDriveTrain(YamlBase):
    model_config = ConfigDict(title="TurbineDriveTrain")

    type: Literal[YamlDriveTrainType.TURBINE_DRIVE_TRAIN] = Field(
        ...,
        description="Defines the type of drive train. See documentation for more information.",
        title="TYPE",
    )
    name: str

    fuel: YamlTemporalModel[str] = Field(
        None,
        title="FUEL",
        description="The fuel used by the turbine." "\n\n$ECALC_DOCS_KEYWORDS_URL/FUEL",
    )

    turbine_model: YamlTemporalModel[
        str
    ]  # Reference to Models? should be YamlTurbine. Look into what we can do about COMPRESSOR_SAMPLED, doesn't make sense in new structure.


YamlDriveTrain = YamlElectricalDriveTrain | YamlTurbineDriveTrain
