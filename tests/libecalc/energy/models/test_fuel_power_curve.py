import numpy as np
import pytest

from libecalc.common.errors.ecalc_validation_error import EcalcValidationException
from libecalc.energy.models.fuel_power_curve import FuelPowerCurve


def test_rejects_non_finite_values():
    with pytest.raises(EcalcValidationException, match="finite"):
        FuelPowerCurve(np.array([10000.0, np.nan]), np.array([2.0, 7.0]))
