from typing import Literal

import numpy as np
from numpy.typing import NDArray
from scipy.interpolate import interp1d

from libecalc.common.energy_model_type import EnergyModelType
from libecalc.common.list.adjustment import transform_linear
from libecalc.common.string.string_utils import generate_id
from libecalc.common.utils.rates import Rates
from libecalc.domain.process.generator_set.generator_set_validator import GeneratorSetSampledValidator
from libecalc.domain.process.process_system import ProcessUnit, TStream


class GeneratorSetProcessUnit(ProcessUnit):
    typ: Literal[EnergyModelType.GENERATOR_SET_SAMPLED] = EnergyModelType.GENERATOR_SET_SAMPLED

    def __init__(
        self,
        name: str,
        headers: list[str],
        data: list[list[float]],
        energy_usage_adjustment_constant: float,
        energy_usage_adjustment_factor: float,
    ):
        self._name = name
        self._id = generate_id(self._name)
        self.headers = headers
        self.data = data
        self.energy_usage_adjustment_constant = energy_usage_adjustment_constant
        self.energy_usage_adjustment_factor = energy_usage_adjustment_factor
        self.validator = GeneratorSetSampledValidator(headers, data, self.typ.value)
        self.validator.validate()

        # Initialize the generator model
        fuel_values = self.fuel_values
        power_values = self.power_values
        fuel_values = transform_linear(
            np.array(fuel_values),
            constant=energy_usage_adjustment_constant,
            factor=energy_usage_adjustment_factor,
        )
        self._func = interp1d(
            power_values,
            fuel_values.tolist(),
            fill_value=(min(fuel_values), max(fuel_values)),
            bounds_error=False,
        )

    @property
    def fuel_values(self) -> list[float]:
        fuel_index = self.headers.index("FUEL")
        return [row[fuel_index] for row in zip(*self.data)]

    @property
    def power_values(self) -> list[float]:
        power_index = self.headers.index("POWER")
        return [row[power_index] for row in zip(*self.data)]

    @property
    def max_capacity(self) -> float:
        return self._func.x.max()

    @property
    def max_fuel(self) -> float:
        return self._func.y.max()

    def get_id(self) -> str:
        return self._id

    def get_type(self) -> str:
        return self.typ.value

    def get_name(self) -> str:
        return self._name

    def get_streams(self) -> list[TStream]:
        return []

    def evaluate_fuel_usage(self, x: NDArray[np.float64]) -> NDArray[np.float64]:
        """Ensure zero power consumption return zero fuel consumption. I.e. equipment is turned off."""
        x = np.asarray(x, dtype=np.float64)
        return np.where(x > 0, self._func(x), 0.0)

    def evaluate_power_capacity_margin(self, x: NDArray[np.float64]) -> NDArray[np.float64]:
        """Calculate the capacity margin on the el2fuel function if using sampled data.
        If using el2fuel factor, there is no margin.

        E.g.
            max sampled power is 50, and you require 40 -> 50 - 40 = 10.
            max sampled power is 50, and you require 60 -> 50 - 60 = -10
        """
        return np.full_like(x, fill_value=self.max_capacity, dtype=np.float64) - x

    @staticmethod
    def clean_nan_values(values: NDArray[np.float64]) -> NDArray[np.float64]:
        """
        Handles NaN values in a consistent manner:
        - Forward fills NaN values.
        - Replaces remaining NaN values with 0.0.

        Args:
            values: A numpy array of float values.

        Returns:
            A numpy array with NaN values handled.
        """

        result = Rates.forward_fill_nan_values(rates=values)  # Fill NaN values
        result = np.nan_to_num(result)  # By convention, we change remaining NaN-values to 0 regardless of extrapolation
        return result

    def __eq__(self, other):
        if not isinstance(other, GeneratorSetProcessUnit):
            return False
        return (
            self.typ == other.typ
            and self.headers == other.headers
            and self.data == other.data
            and self.get_name() == other.get_name()
            and self.get_id() == other.get_id()
            and self.energy_usage_adjustment_constant == other.energy_usage_adjustment_constant
            and self.energy_usage_adjustment_factor == other.energy_usage_adjustment_factor
        )
