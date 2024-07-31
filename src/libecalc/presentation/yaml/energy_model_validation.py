import datetime

from libecalc.presentation.yaml.yaml_keywords import EcalcYamlKeywords


def validate_energy_usage_models(model: dict, consumer_name: str):
    energy_models = []
    for key, value in model.items():
        if isinstance(key, datetime.date) and value[EcalcYamlKeywords.type] not in energy_models:
            energy_models.append(value[EcalcYamlKeywords.type])

    if len(energy_models) > 1:
        energy_models_list = ", ".join(energy_models)
        raise ValueError(
            "Energy model type cannot change over time within a single consumer."
            f" The model type is changed for '{consumer_name}': {energy_models_list}",
        )
