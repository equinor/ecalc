from typing import Literal

import numpy as np
from scipy.interpolate import interp1d

from libecalc.common.energy_model_type import EnergyModelType
from libecalc.common.list.adjustment import transform_linear
from libecalc.common.string.string_utils import generate_id
from libecalc.domain.infrastructure.energy_components.generator_set.generator_set_validator import GeneratorSetValidator
from libecalc.domain.resource import Resource


class GeneratorSetModel:
    """
    Provides an interpolation-based mapping from electrical power output to fuel consumption for a generator set,
    based on sampled data.

    This class validates and stores sampled generator set data (power vs. fuel usage), applies optional linear
    adjustments, and exposes methods to evaluate fuel usage and available capacity margin for a given power demand.
    It does not model process streams, but focuses solely on the energy domain.
    """

    typ: Literal[EnergyModelType.GENERATOR_SET_SAMPLED] = EnergyModelType.GENERATOR_SET_SAMPLED

    def __init__(
        self,
        name: str,
        resource: Resource,
        energy_usage_adjustment_constant: float,
        energy_usage_adjustment_factor: float,
    ):
        self._name = name
        self._id = generate_id(self._name)
        self.resource = resource
        self.energy_usage_adjustment_constant = energy_usage_adjustment_constant
        self.energy_usage_adjustment_factor = energy_usage_adjustment_factor
        self.validator = GeneratorSetValidator(resource=self.resource, typ=self.typ.value)
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
        return [float(x) for x in self.resource.get_column("FUEL")]

    @property
    def electricity2fuel_power_axis(self) -> list[float]:
        return [float(x) for x in self.resource.get_column("POWER")]

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

    def evaluate_fuel_usage(self, power: float) -> float:
        """Return the fuel usage for a given power input."""
        return float(self._func(power)) if power > 0 else 0.0

    def evaluate_power_capacity_margin(self, power: float) -> float:
        """Return the capacity margin for a given power input."""
        return float(self.max_capacity - power)

    def __eq__(self, other):
        """
        Compare two GeneratorSetModel instances for equality based on their unique identity (_id).

        Args:
            other: The object to compare with.

        Returns:
            True if both are GeneratorSetModel instances with the same _id, False otherwise.
        """
        if not isinstance(other, GeneratorSetModel):
            return False
        return self.get_id() == other.get_id()

    def __hash__(self):
        """
        Return the hash based on the unique identity (_id) of the GeneratorSetModel.

        Returns:
            An integer hash value.
        """
        return hash(self.get_id())
