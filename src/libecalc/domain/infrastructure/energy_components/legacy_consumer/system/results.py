from __future__ import annotations

import abc
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

import numpy as np
from numpy.typing import NDArray

from libecalc.common.logger import logger
from libecalc.common.time_utils import Periods
from libecalc.domain.component_validation_error import ComponentValidationException
from libecalc.domain.infrastructure.energy_components.legacy_consumer.consumer_function.results import (
    ConsumerFunctionResultBase,
)
from libecalc.domain.infrastructure.energy_components.legacy_consumer.consumer_function.types import (
    ConsumerFunctionType,
)
from libecalc.domain.process.core.results import EnergyFunctionResult


class SystemComponentResult(Protocol):
    @abc.abstractmethod
    def __len__(self) -> int: ...

    @property
    @abc.abstractmethod
    def is_valid(self) -> list[bool]: ...

    energy_usage: list[float]
    power: list[float] | None


class ConsumerSystemOperationalSettingResult:
    def __init__(self, consumer_results: list[SystemComponentResult]):
        self.consumer_results = consumer_results

    def __len__(self) -> int:
        return len(self.consumer_results[0])

    @property
    def energy_usage(self) -> NDArray:
        return np.sum([np.asarray(result.energy_usage) for result in self.consumer_results], axis=0)

    @property
    def power(self) -> NDArray:
        return np.sum(
            [
                np.asarray(result.power) if result.power is not None else np.zeros_like(result.energy_usage)
                for result in self.consumer_results
            ],
            axis=0,
        )

    @property
    def is_valid(self) -> NDArray:
        return np.multiply.reduce([np.asarray(result.is_valid) for result in self.consumer_results], axis=0).astype(
            bool
        )

    @property
    def indices_outside_capacity(self) -> NDArray:
        return np.asarray([i for i, is_valid in enumerate(self.is_valid) if not is_valid])

    @property
    def indices_within_capacity(self) -> NDArray[np.float64]:
        return np.asarray([i for i, is_valid in enumerate(self.is_valid) if is_valid])


@dataclass
class SystemComponentResultWithName:
    name: str
    result: SystemComponentResult


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
        consumer_results: list[list[SystemComponentResultWithName]],
        cross_over_used: NDArray | None = None,
        # 0 or 1 whether cross over is used for this result (1=True, 0=False)
        periods: Periods = None,
        is_valid: NDArray = None,
        energy_usage: NDArray = None,
        energy_usage_before_power_loss_factor: NDArray | None = None,
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
            power_loss_factor=power_loss_factor,
            energy_function_result=energy_function_result,
            power=power,
        )
        self.operational_setting_used = operational_setting_used
        self.consumer_results = consumer_results
        self.cross_over_used = cross_over_used

    def extend(self, other) -> ConsumerSystemConsumerFunctionResult:
        if not isinstance(self, type(other)):
            msg = "Mixing CONSUMER_SYSTEM with non-CONSUMER_SYSTEM is no longer supported."
            logger.warning(msg)
            raise ComponentValidationException(
                message=msg,
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
