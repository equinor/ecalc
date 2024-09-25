from datetime import datetime
from typing import Dict, Union

from libecalc.presentation.yaml.yaml_types.components.legacy.energy_usage_model import (
    YamlEnergyUsageModelCompressor,
    YamlEnergyUsageModelCompressorSystem,
    YamlEnergyUsageModelCompressorTrainMultipleStreams,
    YamlEnergyUsageModelDirect,
    YamlEnergyUsageModelTabulated,
)


def validate_energy_usage_models(
    model: Union[
        YamlEnergyUsageModelDirect,
        YamlEnergyUsageModelCompressor,
        YamlEnergyUsageModelCompressorSystem,
        YamlEnergyUsageModelTabulated,
        YamlEnergyUsageModelCompressorTrainMultipleStreams,
        Dict[
            datetime,
            Union[
                YamlEnergyUsageModelDirect,
                YamlEnergyUsageModelCompressor,
                YamlEnergyUsageModelCompressorSystem,
                YamlEnergyUsageModelTabulated,
                YamlEnergyUsageModelCompressorTrainMultipleStreams,
            ],
        ],
    ],
    consumer_name: str,
):
    if isinstance(model, dict):
        # Temporal model since dict
        energy_model_types = []
        for value in model.values():
            if value.type not in energy_model_types:
                energy_model_types.append(value.type)

        if len(energy_model_types) > 1:
            energy_models_list = ", ".join(energy_model_types)
            raise ValueError(
                "Energy model type cannot change over time within a single consumer."
                f" The model type is changed for '{consumer_name}': {energy_models_list}",
            )
