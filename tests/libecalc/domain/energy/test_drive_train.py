import pytest

from libecalc.domain.energy.drive_train.drive_train import GeneratorSetDriveTrainResult, TurbineDriveTrainResult
from libecalc.domain.energy.drive_train.generator_set_drive_train import GeneratorSetDriveTrain
from libecalc.domain.energy.drive_train.turbine_drive_train import TurbineDriveTrain
from libecalc.domain.energy.rotating_equipment.shaft_power_consumer import ShaftPowerConsumer
from libecalc.domain.infrastructure.energy_components.generator_set.generator_set_model import GeneratorSetModel
from libecalc.domain.infrastructure.energy_components.turbine.turbine import Turbine
from libecalc.presentation.yaml.yaml_entities import MemoryResource


def _make_consumer(
    inlet_enthalpy=200_000.0,
    outlet_enthalpy=250_000.0,
    mass_rate=36_000.0,
):
    """Default: delta_h=50kJ/kg, 10 kg/s → 0.5 MW shaft power."""
    return ShaftPowerConsumer(
        inlet_enthalpy_joule_per_kg=inlet_enthalpy,
        outlet_enthalpy_joule_per_kg=outlet_enthalpy,
        mass_rate_kg_per_h=mass_rate,
    )


@pytest.fixture
def turbine() -> Turbine:
    """Simple turbine: linear efficiency 0.1–0.5 over loads 0–10 MW."""
    return Turbine(
        loads=[0, 5, 10],
        lower_heating_value=38000,
        efficiency_fractions=[0.1, 0.3, 0.5],
        energy_usage_adjustment_factor=1.0,
        energy_usage_adjustment_constant=0.0,
    )


@pytest.fixture
def generator_set() -> GeneratorSetModel:
    """Simple generator set: max 2 MW, linear fuel curve."""
    return GeneratorSetModel(
        name="test_genset",
        resource=MemoryResource(
            headers=["POWER", "FUEL"],
            data=[[0, 1, 2], [0, 100, 200]],
        ),
    )


class TestShaftPowerConsumer:
    def test_power_from_enthalpy_rise(self):
        """P = delta_h × mass_rate = 50kJ/kg × 10 kg/s = 0.5 MW."""
        assert _make_consumer().get_shaft_power_demand_mw() == 0.5

    def test_zero_rate(self):
        """No flow → no power."""
        assert _make_consumer(mass_rate=0.0).get_shaft_power_demand_mw() == 0.0


class TestTurbineDriveTrain:
    def test_evaluate(self, turbine):
        """Passes required mechanical power to turbine, returns fuel and load status."""
        dt = TurbineDriveTrain(turbine=turbine, rotating_equipment=[_make_consumer()])
        result = dt.evaluate()

        assert isinstance(result, TurbineDriveTrainResult)
        assert result.shaft_power_demand_mw == 0.5
        assert result.required_mechanical_power_mw == 0.5
        assert result.fuel_rate_sm3_per_day > 0
        assert result.exceeds_maximum_load is False

    def test_mechanical_efficiency(self, turbine):
        """50% efficiency → turbine must deliver 1.0 MW for 0.5 MW shaft power."""
        dt = TurbineDriveTrain(
            turbine=turbine,
            rotating_equipment=[_make_consumer()],
            mechanical_efficiency=0.5,
        )
        result = dt.evaluate()
        assert result.shaft_power_demand_mw == 0.5
        assert result.required_mechanical_power_mw == 1.0


class TestGeneratorSetDriveTrain:
    def test_evaluate(self, generator_set):
        """Passes required electrical power to generator set, returns fuel and capacity margin."""
        dt = GeneratorSetDriveTrain(generator_set=generator_set, rotating_equipment=[_make_consumer()])
        result = dt.evaluate()

        assert isinstance(result, GeneratorSetDriveTrainResult)
        assert result.shaft_power_demand_mw == 0.5
        assert result.required_electrical_power_mw == 0.5
        assert result.fuel_rate_sm3_per_day == pytest.approx(50.0)
        assert result.power_capacity_margin_mw == pytest.approx(1.5)
        assert result.exceeds_maximum_load is False

    def test_exceeds_maximum_load(self, generator_set):
        """Power demand > max capacity → exceeds maximum load."""
        # Generator set max is 2 MW. Consumer needs 2.5 MW.
        consumer = _make_consumer(outlet_enthalpy=450_000.0)  # delta_h=250kJ/kg, 10 kg/s → 2.5 MW
        dt = GeneratorSetDriveTrain(generator_set=generator_set, rotating_equipment=[consumer])
        result = dt.evaluate()

        assert result.exceeds_maximum_load is True
        assert result.power_capacity_margin_mw < 0

    def test_multiple_consumers(self, generator_set):
        """Two consumers: 0.5 MW + 2.0 MW = 2.5 MW total shaft power."""
        c1 = _make_consumer()  # 0.5 MW
        c2 = _make_consumer(inlet_enthalpy=100_000.0, outlet_enthalpy=200_000.0, mass_rate=72_000.0)  # 2.0 MW
        dt = GeneratorSetDriveTrain(generator_set=generator_set, rotating_equipment=[c1, c2])
        result = dt.evaluate()

        assert result.shaft_power_demand_mw == 2.5
        assert result.required_electrical_power_mw == 2.5
