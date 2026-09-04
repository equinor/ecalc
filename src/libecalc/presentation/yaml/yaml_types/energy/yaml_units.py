from typing import Annotated

from pydantic import Field

from libecalc.presentation.yaml.yaml_types.energy.yaml_consumers import (
    YamlCompressor,
    YamlDieselConsumer,
    YamlElectricalConsumer,
    YamlFuelGasConsumer,
    YamlPump,
)
from libecalc.presentation.yaml.yaml_types.energy.yaml_converters import (
    YamlElectricalMotor,
    YamlGasTurbine,
    YamlGeneratorSet,
)
from libecalc.presentation.yaml.yaml_types.energy.yaml_junctions import YamlElectricalBus, YamlFuelGasManifold
from libecalc.presentation.yaml.yaml_types.energy.yaml_transporters import YamlElectricalCable

YamlEnergyNetworkUnit = Annotated[
    YamlGeneratorSet
    | YamlGasTurbine
    | YamlElectricalMotor
    | YamlElectricalCable
    | YamlElectricalBus
    | YamlFuelGasManifold
    | YamlElectricalConsumer
    | YamlCompressor
    | YamlPump
    | YamlFuelGasConsumer
    | YamlDieselConsumer,
    Field(discriminator="type"),
]
