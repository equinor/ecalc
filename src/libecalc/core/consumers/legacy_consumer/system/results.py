from __future__ import annotations

from enum import Enum
from typing import List, Literal, Optional, Union

import numpy as np
from numpy.typing import NDArray
from pydantic import BaseModel, ConfigDict

from libecalc.common.logger import logger
from libecalc.core.consumers.legacy_consumer.consumer_function.results import (
    ConsumerFunctionResultBase,
)
from libecalc.core.consumers.legacy_consumer.consumer_function.types import (
    ConsumerFunctionType,
)
from libecalc.core.consumers.legacy_consumer.system.operational_setting import (
    ConsumerSystemOperationalSetting,
)
from libecalc.core.models.results import CompressorTrainResult, PumpModelResult
from libecalc.core.result.results import ConsumerModelResult


class ConsumerSystemComponentResult(BaseModel):
    name: str
    consumer_model_result: Union[PumpModelResult, CompressorTrainResult]

    @property
    def energy_usage(self) -> List[Optional[float]]:
        return self.consumer_model_result.energy_usage

    @property
    def power(self) -> NDArray[np.float64]:
        if self.consumer_model_result.power is not None:
            return np.asarray(self.consumer_model_result.power)
        else:
            return np.zeros_like(self.consumer_model_result.energy_usage)

    @property
    def rate(self) -> List[Optional[float]]:
        return self.consumer_model_result.rate


class PumpResult(ConsumerSystemComponentResult):
    consumer_model_result: PumpModelResult

    @property
    def fluid_density(self):
        return self.consumer_model_result.fluid_density


class CompressorResult(ConsumerSystemComponentResult):
    consumer_model_result: Union[ConsumerModelResult, CompressorTrainResult]


class ConsumerSystemOperationalSettingResult(BaseModel):
    consumer_results: List[ConsumerSystemComponentResult]
    model_config = ConfigDict(frozen=True)

    @property
    def total_energy_usage(self) -> NDArray[np.float64]:
        total_energy_usage = np.sum(
            [np.asarray(result.energy_usage) for result in self.consumer_results],
            axis=0,
        )
        return np.array(total_energy_usage)

    @property
    def total_power(self) -> NDArray[np.float64]:
        total_power = np.sum(
            [np.asarray(result.power) for result in self.consumer_results],
            axis=0,
        )
        return np.array(total_power)

    @property
    def indices_outside_capacity(self) -> NDArray[np.float64]:
        invalid_indices = np.full_like(self.total_energy_usage, fill_value=0)

        for result in self.consumer_results:
            energy_function_result = result.consumer_model_result
            if isinstance(energy_function_result, (CompressorTrainResult, PumpModelResult)):
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

    typ: Literal[ConsumerFunctionType.SYSTEM] = ConsumerFunctionType.SYSTEM  # type: ignore[valid-type]

    operational_setting_used: NDArray[np.float64]  # integers in the range of number of operational settings
    operational_settings: List[List[ConsumerSystemOperationalSetting]]
    operational_settings_results: List[List[ConsumerSystemOperationalSettingResult]]
    consumer_results: List[List[ConsumerSystemComponentResult]]
    cross_over_used: Optional[
        NDArray[np.float64]
    ] = None  # 0 or 1 whether cross over is used for this result (1=True, 0=False)

    def extend(self, other) -> ConsumerSystemConsumerFunctionResult:
        if not isinstance(self, type(other)):
            msg = f"{self.__repr_name__()} Mixing CONSUMER_SYSTEM with non-CONSUMER_SYSTEM is no longer supported."
            logger.warning(msg)
            raise ValueError(msg)

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
            else:
                msg = (
                    f"{self.__repr_name__()} attribute {attribute} does not have an append method."
                    f" You should not land here. Please contact the eCalc Support."
                )
                logger.warning(msg)
                raise NotImplementedError(msg)
        return self
