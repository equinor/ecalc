from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from libecalc.common.errors.ecalc_validation_error import EcalcValidationException
from libecalc.energy.models.combustion_engine_fuel_model import CombustionEngineFuelModel
from libecalc.energy.models.curve_validation import CurveLabels, validate_curve


class SampledGeneratorSetFuelModel:
    """Generator set fuel consumption [Sm3/day] from the electrical power [MW], interpolated from a curve."""

    def __init__(self, powers: Sequence[float], fuels: Sequence[float]) -> None:
        validate_generator_curve(powers, fuels)
        self._powers = np.asarray(powers, dtype=np.float64)
        self._fuels = np.asarray(fuels, dtype=np.float64)

    @property
    def max_power(self) -> float:
        return float(self._powers[-1])

    @property
    def powers(self) -> list[float]:
        return self._powers.tolist()

    @property
    def fuels(self) -> list[float]:
        return self._fuels.tolist()

    def fuel_for_power(self, power: float) -> float:
        assert power >= 0, f"Power must not be negative, got {power}."
        if power == 0:
            return 0.0
        # Same as the legacy generator set: outside the curve the lowest and highest fuel are used
        return float(np.interp(power, self._powers, self._fuels, left=self._fuels.min(), right=self._fuels.max()))


class EngineDrivenGeneratorSetFuelModel:
    """Generator set fuel consumption from an underlying turbine/diesel engine model and a generator efficiency.

    The engine model expects its own shaft/load power, so electrical power demand is converted to load by
    dividing by the generator efficiency before delegating to the engine model.
    """

    def __init__(self, engine_fuel_model: CombustionEngineFuelModel, generator_efficiency: float) -> None:
        validate_generator_efficiency(generator_efficiency)
        self._engine_fuel_model = engine_fuel_model
        self._generator_efficiency = generator_efficiency

    @property
    def max_power(self) -> float:
        return self._engine_fuel_model.max_power * self._generator_efficiency

    def fuel_for_power(self, power: float) -> float:
        assert power >= 0, f"Power must not be negative, got {power}."
        load = power / self._generator_efficiency
        return self._engine_fuel_model.fuel_for_power(load)


GeneratorSetFuelModel = SampledGeneratorSetFuelModel | EngineDrivenGeneratorSetFuelModel


_GENERATOR_LABELS = CurveLabels(subject="generator", x="power", y="fuel")


def validate_generator_curve(powers: Sequence[float], fuels: Sequence[float]) -> None:
    validate_curve(powers, fuels, _GENERATOR_LABELS)
    if any(fuel < 0 for fuel in fuels):
        raise EcalcValidationException("Generator fuel must not be negative.")


def validate_generator_efficiency(generator_efficiency: float) -> None:
    if not 0 < generator_efficiency <= 1:
        raise EcalcValidationException(
            f"Generator efficiency must be a fraction above 0 and up to 1, got {generator_efficiency}."
        )
