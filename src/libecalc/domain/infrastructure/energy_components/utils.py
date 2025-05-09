from datetime import datetime
from typing import Any

from libecalc.common.energy_usage_type import EnergyUsageType
from libecalc.common.time_utils import Period
from libecalc.domain.component_validation_error import (
    ComponentValidationException,
    ModelValidationError,
)
from libecalc.domain.process.dto import ConsumerFunction
from libecalc.presentation.yaml.validation_errors import Location


def check_model_energy_usage_type(model_data: dict[Period, ConsumerFunction], energy_type: EnergyUsageType):
    for model in model_data.values():
        if model.energy_usage_type != energy_type:
            raise ComponentValidationException(
                errors=[
                    ModelValidationError(
                        message=f"Model does not consume {energy_type.value}",
                        location=Location(keys=[]),
                    )
                ]
            )
    return model_data


def _convert_keys_in_dictionary_from_str_to_periods(data: dict[str | Period, Any]) -> dict[Period, Any]:
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
