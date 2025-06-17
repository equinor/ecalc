from datetime import datetime
from typing import Protocol


class HasType(Protocol):
    type: str


def validate_energy_usage_models(
    model: HasType | dict[datetime, HasType],
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
