import numpy as np
import pytest

from libecalc.common.errors.ecalc_validation_error import (
    EcalcValidationException,
    ProcessEqualLengthValidationException,
)
from libecalc.common.errors.exceptions import IllegalStateException, InvalidColumnException
from libecalc.domain.infrastructure.energy_components.legacy_consumer.tabulated.tabular_energy_function import (
    TabularEnergyFunction,
)
from libecalc.energy.models.tabular import TabularModel


class TestTabularModel1D:
    def test_matches_legacy(self):
        variables = {"RATE": [0.0, 50.0, 100.0]}
        function_values = [0.0, 500.0, 1000.0]
        model = TabularModel(variables=variables, function_values=function_values)
        legacy = TabularEnergyFunction(headers=["RATE", "FUEL"], data=[variables["RATE"], function_values])

        for rate in (0.0, 25.0, 50.0, 75.0, 100.0):
            expected = float(np.asarray(legacy.interpolate(np.asarray([rate]))).reshape(-1)[0])
            assert model.evaluate({"RATE": rate}) == pytest.approx(expected)

    def test_out_of_envelope_returns_nan(self):
        model = TabularModel(variables={"RATE": [0.0, 100.0]}, function_values=[0.0, 1000.0])
        assert np.isnan(model.evaluate({"RATE": -1.0}))
        assert np.isnan(model.evaluate({"RATE": 101.0}))


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
    def test_requires_equal_length_columns(self):
        with pytest.raises(ProcessEqualLengthValidationException):
            TabularModel(variables={"RATE": [0.0, 50.0]}, function_values=[0.0, 500.0, 1000.0])

    def test_evaluate_requires_all_variables(self):
        model = TabularModel(
            variables={"RATE": [0.0, 100.0, 0.0, 100.0], "SUCTION_PRESSURE": [10.0, 10.0, 20.0, 20.0]},
            function_values=[0.0, 1000.0, 100.0, 1100.0],
        )
        with pytest.raises(IllegalStateException, match="SUCTION_PRESSURE"):
            model.evaluate({"RATE": 50.0})

    @pytest.mark.parametrize("bad", [float("nan"), float("inf")])
    def test_rejects_non_finite_values(self, bad):
        with pytest.raises(InvalidColumnException):
            TabularModel(variables={"RATE": [0.0, bad, 2.0]}, function_values=[0.0, 1.0, 2.0])
        with pytest.raises(InvalidColumnException):
            TabularModel(variables={"RATE": [0.0, 1.0, 2.0]}, function_values=[0.0, bad, 2.0])

    def test_rejects_negative_energy_usage(self):
        with pytest.raises(InvalidColumnException, match="negative"):
            TabularModel(variables={"RATE": [0.0, 1.0, 2.0]}, function_values=[0.0, -1.0, 2.0])

    def test_rejects_too_few_unique_rows(self):
        with pytest.raises(EcalcValidationException, match="unique rows"):
            TabularModel(variables={"RATE": [1.0, 1.0, 1.0]}, function_values=[1.0, 1.0, 1.0])

    def test_rejects_conflicting_duplicate_rows(self):
        with pytest.raises(EcalcValidationException, match="more than once"):
            TabularModel(variables={"RATE": [0.0, 1.0, 1.0]}, function_values=[0.0, 1.0, 3.0])

    def test_accepts_exact_duplicate_rows(self):
        model = TabularModel(variables={"RATE": [0.0, 1.0, 1.0]}, function_values=[0.0, 1.0, 1.0])
        assert model.evaluate({"RATE": 0.5}) == pytest.approx(0.5)

    @pytest.mark.parametrize(
        "variables",
        [{"RATE": []}, {"RATE": [1.0]}, {"RATE": [1.0, 2.0], "PRESSURE": [1.0, 2.0]}],
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
