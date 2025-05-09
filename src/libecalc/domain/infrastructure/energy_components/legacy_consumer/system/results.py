from __future__ import annotations

from enum import Enum

import numpy as np
from numpy.typing import NDArray

from libecalc.common.logger import logger
from libecalc.common.time_utils import Periods
from libecalc.core.result.results import ConsumerModelResult
from libecalc.domain.component_validation_error import (
    ComponentValidationException,
    ModelValidationError,
)
from libecalc.domain.infrastructure.energy_components.legacy_consumer.consumer_function.results import (
    ConsumerFunctionResultBase,
)
from libecalc.domain.infrastructure.energy_components.legacy_consumer.consumer_function.types import (
    ConsumerFunctionType,
)
from libecalc.domain.infrastructure.energy_components.legacy_consumer.system.operational_setting import (
    ConsumerSystemOperationalSetting,
)
from libecalc.domain.process.core.results import CompressorTrainResult, EnergyFunctionResult, PumpModelResult
from libecalc.presentation.yaml.validation_errors import Location


class ConsumerSystemComponentResult:
    def __init__(self, name: str, consumer_model_result: PumpModelResult | CompressorTrainResult):
        self.name = name
        self.consumer_model_result = consumer_model_result

    @property
    def energy_usage(self) -> list[float | None]:
        return self.consumer_model_result.energy_usage

    @property
    def power(self) -> NDArray:
        if self.consumer_model_result.power is not None:
            return np.asarray(self.consumer_model_result.power)
        else:
            return np.zeros_like(self.consumer_model_result.energy_usage)

    @property
    def rate(self) -> list[float | None]:
        return self.consumer_model_result.rate


class PumpResult(ConsumerSystemComponentResult):
    def __init__(self, name: str, consumer_model_result: PumpModelResult):
        super().__init__(name, consumer_model_result)

    @property
    def fluid_density(self):
        return self.consumer_model_result.fluid_density


class CompressorResult(ConsumerSystemComponentResult):
    def __init__(self, name: str, consumer_model_result: ConsumerModelResult | CompressorTrainResult):
        super().__init__(name, consumer_model_result)


class ConsumerSystemOperationalSettingResult:
    def __init__(self, consumer_results: list[ConsumerSystemComponentResult]):
        self.consumer_results = consumer_results

    @property
    def total_energy_usage(self) -> NDArray:
        total_energy_usage = np.sum(
            [np.asarray(result.energy_usage) for result in self.consumer_results],
            axis=0,
        )
        return np.array(total_energy_usage)

    @property
    def total_power(self) -> NDArray:
        total_power = np.sum(
            [np.asarray(result.power) for result in self.consumer_results],
            axis=0,
        )
        return np.array(total_power)

    @property
    def indices_outside_capacity(self) -> NDArray:
        invalid_indices = np.full_like(self.total_energy_usage, fill_value=0)

        for result in self.consumer_results:
            energy_function_result = result.consumer_model_result
            if isinstance(energy_function_result, CompressorTrainResult | PumpModelResult):
                invalid_indices = np.add(
                    invalid_indices,
                    np.array([0 if x else 1 for x in energy_function_result.is_valid]),
                )
            else:
                raise NotImplementedError(
                    f"Consumer system result assembly has not been implemented for {type(energy_function_result)}."
                    f" Please contact eCalc support."
                )
        return np.argwhere(np.where(np.logical_or(invalid_indices > 0, np.isnan(self.total_energy_usage)), 1, 0))[:, 0]

    @property
    def indices_within_capacity(self) -> NDArray[np.float64]:
        return np.setdiff1d(np.arange(self.total_energy_usage.shape[0]), self.indices_outside_capacity)


class ConsumerSystemConsumerFunctionResult(ConsumerFunctionResultBase):
    """Class for holding results for a consumer system evaluation.

    operational_setting_used: an array - one for each time step evaluated - for which of
    the operational settings where used (in obtaining the final energy usage result)
    operational_settings: a list for each operational setting. Each element contains data
    of the operational setting, i.e. what rates/pressures/fluid densities for which consumer in
    the system
    operational_settings_results: a list for each operational setting. Each element contain
    data for the energy usage of each consumer in the system in this operational setting.
    """

    def __init__(
        self,
        operational_setting_used: NDArray,
        operational_settings: list[list[ConsumerSystemOperationalSetting]],
        operational_settings_results: list[list[ConsumerSystemOperationalSettingResult]],
        consumer_results: list[list[ConsumerSystemComponentResult]],
        cross_over_used: NDArray | None = None,
        # 0 or 1 whether cross over is used for this result (1=True, 0=False)
        periods: Periods = None,
        is_valid: NDArray = None,
        energy_usage: NDArray = None,
        energy_usage_before_power_loss_factor: NDArray | None = None,
        condition: NDArray | None = None,
        power_loss_factor: NDArray | None = None,
        energy_function_result: EnergyFunctionResult | list[EnergyFunctionResult] | None = None,
        power: NDArray | None = None,
    ):
        super().__init__(
            typ=ConsumerFunctionType.SYSTEM,
            periods=periods,
            is_valid=is_valid,
            energy_usage=energy_usage,
            energy_usage_before_power_loss_factor=energy_usage_before_power_loss_factor,
            condition=condition,
            power_loss_factor=power_loss_factor,
            energy_function_result=energy_function_result,
            power=power,
        )
        self.operational_setting_used = operational_setting_used
        self.operational_settings = operational_settings
        self.operational_settings_results = operational_settings_results
        self.consumer_results = consumer_results
        self.cross_over_used = cross_over_used

    def extend(self, other) -> ConsumerSystemConsumerFunctionResult:
        if not isinstance(self, type(other)):
            msg = "Mixing CONSUMER_SYSTEM with non-CONSUMER_SYSTEM is no longer supported."
            logger.warning(msg)
            raise ComponentValidationException(
                errors=[
                    ModelValidationError(
                        name=self.__repr_name__(),
                        message=msg,
                        location=Location([self.__repr_name__()]),  # for now, we will use the name as the location
                    )
                ]
            )

        for attribute, values in self.__dict__.items():
            other_values = other.__getattribute__(attribute)

            if values is None or other_values is None or isinstance(values, Enum):
                continue
            elif isinstance(values, np.ndarray):
                self.__setattr__(attribute, np.append(values, other_values))
            elif isinstance(values, list):
                if isinstance(other_values, list):
                    values.extend(other_values)
                else:
                    values.append(other_values)
            elif isinstance(values, Periods):
                self.__setattr__(attribute, values + other_values)
            else:
                msg = (
                    f"{self.__repr_name__()} attribute {attribute} does not have an append method."
                    f" You should not land here. Please contact the eCalc Support."
                )
                logger.warning(msg)
                raise NotImplementedError(msg)
        return self
