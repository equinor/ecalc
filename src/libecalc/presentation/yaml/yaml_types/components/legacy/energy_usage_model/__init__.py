from typing import Annotated, Union

from pydantic import Field

from libecalc.presentation.yaml.yaml_types.components.legacy.energy_usage_model.yaml_energy_usage_model_compressor import (
    YamlEnergyUsageModelCompressor,
)
from libecalc.presentation.yaml.yaml_types.components.legacy.energy_usage_model.yaml_energy_usage_model_compressor_train_multiple_streams import (
    YamlEnergyUsageModelCompressorTrainMultipleStreams,
)
from libecalc.presentation.yaml.yaml_types.components.legacy.energy_usage_model.yaml_energy_usage_model_consumer_system import (
    YamlEnergyUsageModelCompressorSystem,
    YamlEnergyUsageModelPumpSystem,
)
from libecalc.presentation.yaml.yaml_types.components.legacy.energy_usage_model.yaml_energy_usage_model_direct import (
    YamlEnergyUsageModelDirectElectricity,
    YamlEnergyUsageModelDirectFuel,
)
from libecalc.presentation.yaml.yaml_types.components.legacy.energy_usage_model.yaml_energy_usage_model_pump import (
    YamlEnergyUsageModelPump,
)
from libecalc.presentation.yaml.yaml_types.components.legacy.energy_usage_model.yaml_energy_usage_model_tabulated import (
    YamlEnergyUsageModelTabulated,
)

YamlElectricityEnergyUsageModel = Annotated[
    Union[
        YamlEnergyUsageModelDirectElectricity,
        YamlEnergyUsageModelCompressor,
        YamlEnergyUsageModelPump,
        YamlEnergyUsageModelCompressorSystem,
        YamlEnergyUsageModelPumpSystem,
        YamlEnergyUsageModelTabulated,
        YamlEnergyUsageModelCompressorTrainMultipleStreams,
    ],
    Field(discriminator="type"),
]
YamlFuelEnergyUsageModel = Annotated[
    Union[
        YamlEnergyUsageModelDirectFuel,
        YamlEnergyUsageModelCompressor,
        YamlEnergyUsageModelCompressorSystem,
        YamlEnergyUsageModelTabulated,
        YamlEnergyUsageModelCompressorTrainMultipleStreams,
    ],
    Field(discriminator="type"),
]
