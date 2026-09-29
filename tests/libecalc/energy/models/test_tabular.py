import numpy as np
import pytest

from libecalc.common.errors.ecalc_validation_error import EcalcValidationException
from libecalc.domain.infrastructure.energy_components.legacy_consumer.tabulated.tabular_energy_function import (
    TabularEnergyFunction,
)
from libecalc.energy.models.tabular import TabularModel


class TestTabularModel2D:
    def test_matches_legacy(self):
        variables = {
            "RATE": [0.0, 100.0, 0.0, 100.0],
            "SUCTION_PRESSURE": [10.0, 10.0, 20.0, 20.0],
        }
        function_values = [0.0, 1000.0, 100.0, 1100.0]
        model = TabularModel(variables=variables, function_values=function_values)
        legacy = TabularEnergyFunction(
            headers=["RATE", "SUCTION_PRESSURE", "FUEL"],
            data=[variables["RATE"], variables["SUCTION_PRESSURE"], function_values],
        )

        for rate, suction_pressure in ((0.0, 10.0), (50.0, 15.0), (100.0, 20.0)):
            point = {"RATE": rate, "SUCTION_PRESSURE": suction_pressure}
            expected = float(np.asarray(legacy.interpolate(np.asarray([rate, suction_pressure]))).reshape(-1)[0])
            assert model.evaluate(point) == pytest.approx(expected, rel=1e-6)


class TestTabularModelValidation:
    def test_rejects_non_finite_values(self):
        with pytest.raises(EcalcValidationException, match="non-finite"):
            TabularModel(variables={"RATE": [0.0, float("nan"), 2.0]}, function_values=[0.0, 1.0, 2.0])

    def test_rejects_negative_energy_usage(self):
        with pytest.raises(EcalcValidationException, match="negative"):
            TabularModel(variables={"RATE": [0.0, 1.0, 2.0]}, function_values=[0.0, -1.0, 2.0])

    def test_rejects_conflicting_duplicate_rows(self):
        with pytest.raises(EcalcValidationException, match="more than once"):
            TabularModel(variables={"RATE": [0.0, 1.0, 1.0]}, function_values=[0.0, 1.0, 3.0])

    @pytest.mark.parametrize(
        "variables",
        [
            {"RATE": []},
            {"RATE": [1.0]},
            {"RATE": [1.0, 1.0, 1.0]},
            {"RATE": [1.0, 2.0], "PRESSURE": [1.0, 2.0]},
        ],
    )
    def test_rejects_too_few_rows(self, variables):
        with pytest.raises(EcalcValidationException, match="at least"):
            TabularModel(variables=variables, function_values=[1.0] * len(next(iter(variables.values()))))

    def test_rejects_points_on_a_line(self):
        with pytest.raises(EcalcValidationException, match="span every variable"):
            TabularModel(
                variables={"RATE": [0.0, 1.0, 2.0], "PRESSURE": [10.0, 10.0, 10.0]},
                function_values=[0.0, 1.0, 2.0],
            )
