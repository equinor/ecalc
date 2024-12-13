from datetime import datetime
from typing import Any, Union

from libecalc.common.energy_usage_type import EnergyUsageType
from libecalc.common.time_utils import Period
from libecalc.dto.models import ConsumerFunction


def check_model_energy_usage_type(model_data: dict[Period, ConsumerFunction], energy_type: EnergyUsageType):
    for model in model_data.values():
        if model.energy_usage_type != energy_type:
            raise ValueError(f"Model does not consume {energy_type.value}")
    return model_data


def _convert_keys_in_dictionary_from_str_to_periods(data: dict[Union[str, Period], Any]) -> dict[Period, Any]:
    if all(isinstance(key, str) for key in data.keys()):
        return {
            Period(
                start=datetime.strptime(period.split(";")[0], "%Y-%m-%d %H:%M:%S"),
                end=datetime.strptime(period.split(";")[1], "%Y-%m-%d %H:%M:%S"),
            ): value
            for period, value in data.items()
        }
    else:
        return data
