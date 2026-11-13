from datetime import datetime

import pytest

from libecalc.common.errors.ecalc_validation_error import EcalcValidationException
from libecalc.common.errors.exceptions import HeaderNotFoundException, InvalidColumnException
from libecalc.common.time_utils import Period, Periods
from libecalc.common.variables import VariablesMap
from libecalc.ecalc_model.equipment.compressor_equipment import CompressorEquipment
from libecalc.energy.energy_types import MechanicalPower
from libecalc.energy.errors import InvalidEnergyNetworkInputError
from libecalc.presentation.yaml.domain.energy import TimeSeriesCompressorSampled
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression
from libecalc.presentation.yaml.yaml_entities import MemoryResource

PERIOD = Period(start=datetime(2020, 1, 1), end=datetime(2021, 1, 1))
RATES = [1000.0, 2000.0, 3000.0]
SHAFT_POWER = [5.0, 10.0, 15.0]


def _resource(**columns: list[float]) -> MemoryResource:
    return MemoryResource(headers=list(columns), data=[list(values) for values in columns.values()])


def _expression(value: float) -> TimeSeriesExpression:
    return TimeSeriesExpression(
        expression=value, expression_evaluator=VariablesMap(periods=Periods(periods=[PERIOD]), variables={})
    )


def _compressor(resource: MemoryResource, **variables: float) -> TimeSeriesCompressorSampled:
    return TimeSeriesCompressorSampled(
        compressor_equipment_id=CompressorEquipment(name="C-1").get_id(),
        name="C-1",
        file="compressor.csv",
        resource=resource,
        **{name: _expression(value) for name, value in variables.items()},
    )


def test_shaft_power_is_looked_up():
    resource = _resource(RATE=RATES, SHAFT_POWER=SHAFT_POWER)
    compressor = _compressor(resource, rate=1500)

    assert compressor.get_shaft_power(PERIOD) == MechanicalPower(7.5)
    assert compressor.get_input_energy_type() is MechanicalPower
    assert compressor.file == "compressor.csv"
    assert compressor.resource is resource


def test_headers_are_case_insensitive():
    compressor = _compressor(_resource(rate=RATES, shaft_power=SHAFT_POWER), rate=1500)
    assert compressor.get_shaft_power(PERIOD) == MechanicalPower(7.5)


@pytest.mark.parametrize("replaced", ["FUEL", "POWER"])
def test_fuel_and_power_columns_rejected(replaced):
    with pytest.raises(InvalidColumnException, match=f"Column '{replaced}' is not supported") as error:
        _compressor(_resource(RATE=RATES, SHAFT_POWER=SHAFT_POWER, **{replaced: SHAFT_POWER}), rate=1500)
    assert error.value.file_mark.column == replaced


def test_missing_shaft_power_rejected():
    with pytest.raises(HeaderNotFoundException, match="Header 'SHAFT_POWER' not found"):
        _compressor(_resource(RATE=RATES), rate=1500)


def test_given_variable_without_column_rejected():
    with pytest.raises(HeaderNotFoundException, match="Header 'SUCTION_PRESSURE' not found"):
        _compressor(_resource(RATE=RATES, SHAFT_POWER=SHAFT_POWER), rate=1500, suction_pressure=20)


def test_column_without_given_variable_rejected():
    resource = _resource(
        RATE=[1000.0, 2000.0, 1000.0, 2000.0],
        SUCTION_PRESSURE=[10.0, 10.0, 20.0, 20.0],
        SHAFT_POWER=[1.0, 2.0, 1.5, 3.0],
    )
    with pytest.raises(InvalidColumnException, match="column for SUCTION_PRESSURE, so SUCTION_PRESSURE") as error:
        _compressor(resource, rate=1500)
    assert error.value.file_mark.column == "SUCTION_PRESSURE"


def test_invalid_samples_rejected_by_factory():
    with pytest.raises(EcalcValidationException, match="wrong number of points"):
        _compressor(_resource(RATE=RATES, SHAFT_POWER=[1.0, 2.0]), rate=1500)


def test_input_outside_sampled_range_rejected():
    compressor = _compressor(_resource(RATE=RATES, SHAFT_POWER=SHAFT_POWER), rate=999_999)
    with pytest.raises(InvalidEnergyNetworkInputError, match="outside the model's sampled range"):
        compressor.get_shaft_power(PERIOD)
