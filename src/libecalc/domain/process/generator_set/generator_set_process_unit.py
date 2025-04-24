from typing import Literal

import numpy as np
from scipy.interpolate import interp1d

from libecalc.common.energy_model_type import EnergyModelType
from libecalc.common.list.adjustment import transform_linear
from libecalc.common.string.string_utils import generate_id
from libecalc.domain.process.generator_set.generator_set_validator import GeneratorSetValidator
from libecalc.domain.process.process_system import LiquidStream, ProcessUnit


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
        self.validator = GeneratorSetValidator(headers, data, self.typ.value)
        self.validator.validate()

        # Initialize the generator model
        fuel_values = self.electricity2fuel_fuel_axis
        power_values = self.electricity2fuel_power_axis
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
    def electricity2fuel_fuel_axis(self) -> list[float]:
        fuel_index = self.headers.index("FUEL")
        return [row[fuel_index] for row in zip(*self.data)]

    @property
    def electricity2fuel_power_axis(self) -> list[float]:
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

    def get_streams(self) -> list[LiquidStream]:
        return []

    def evaluate_fuel_usage(self, power: float) -> float:
        """Return the fuel usage for a given power input."""
        return float(self._func(power)) if power > 0 else 0.0

    def evaluate_power_capacity_margin(self, power: float) -> float:
        """Return the capacity margin for a given power input."""
        return float(self.max_capacity - power)

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
