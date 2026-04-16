"""
Drive trains: sum shaft power from rotating equipment and compute the power
demand that must be supplied — either as mechanical power (turbine, which also
computes fuel directly) or electrical power (electric motor, where fuel depends
on a separate PowerSupply).
"""

import pytest

from libecalc.domain.energy.drive_train.electric_drive_train import ElectricDriveTrain, ElectricDriveTrainResult
from libecalc.domain.energy.drive_train.turbine_drive_train import TurbineDriveTrain, TurbineDriveTrainResult
from libecalc.domain.energy.rotating_equipment.shaft_power_consumer import ShaftPowerConsumer
from libecalc.domain.infrastructure.energy_components.turbine.turbine import Turbine


def _make_consumer(
    inlet_enthalpy=200_000.0,
    outlet_enthalpy=250_000.0,
    mass_rate=36_000.0,
):
    """Default: Δh = 50 kJ/kg, ṁ = 10 kg/s → 0.5 MW shaft power."""
    return ShaftPowerConsumer(
        inlet_enthalpy_joule_per_kg=inlet_enthalpy,
        outlet_enthalpy_joule_per_kg=outlet_enthalpy,
        mass_rate_kg_per_h=mass_rate,
    )


@pytest.fixture
def turbine() -> Turbine:
    """Linear efficiency 0.1–0.5 over loads 0–10 MW. LHV = 38 MJ/Sm³."""
    return Turbine(
        loads=[0, 5, 10],
        lower_heating_value=38000,
        efficiency_fractions=[0.1, 0.3, 0.5],
        energy_usage_adjustment_factor=1.0,
        energy_usage_adjustment_constant=0.0,
    )


class TestTurbineDriveTrain:
    """Turbine burns fuel directly — it is both driver and power source."""

    def test_evaluate(self, turbine):
        """0.5 MW shaft power → turbine produces fuel proportional to load and efficiency."""
        dt = TurbineDriveTrain(turbine=turbine, rotating_equipment=[_make_consumer()])
        result = dt.evaluate()

        assert isinstance(result, TurbineDriveTrainResult)
        assert result.shaft_power_demand_mw == 0.5
        assert result.required_mechanical_power_mw == 0.5
        assert result.fuel_rate_sm3_per_day > 0
        assert result.exceeds_maximum_load is False

    def test_mechanical_efficiency(self, turbine):
        """50% mechanical efficiency → turbine must deliver 1.0 MW for 0.5 MW shaft power."""
        dt = TurbineDriveTrain(
            turbine=turbine,
            rotating_equipment=[_make_consumer()],
            mechanical_efficiency=0.5,
        )
        result = dt.evaluate()
        assert result.shaft_power_demand_mw == 0.5
        assert result.required_mechanical_power_mw == 1.0


class TestElectricDriveTrain:
    """Electric motor — computes electrical power demand without knowing the source."""

    def test_evaluate(self):
        """0.5 MW shaft power → 0.5 MW electrical demand (no mechanical losses)."""
        dt = ElectricDriveTrain(rotating_equipment=[_make_consumer()])
        result = dt.evaluate()

        assert isinstance(result, ElectricDriveTrainResult)
        assert result.shaft_power_demand_mw == 0.5
        assert result.required_electrical_power_mw == 0.5

    def test_mechanical_efficiency(self):
        """50% mechanical efficiency → 1.0 MW electrical for 0.5 MW shaft power."""
        dt = ElectricDriveTrain(
            rotating_equipment=[_make_consumer()],
            mechanical_efficiency=0.5,
        )
        result = dt.evaluate()
        assert result.required_electrical_power_mw == 1.0
        assert result.shaft_power_demand_mw == 0.5

    def test_multiple_consumers(self):
        """Two compressors on one shaft: 0.5 + 2.0 = 2.5 MW total electrical demand."""
        c1 = _make_consumer()  # 0.5 MW
        c2 = _make_consumer(inlet_enthalpy=100_000.0, outlet_enthalpy=200_000.0, mass_rate=72_000.0)  # 2.0 MW
        dt = ElectricDriveTrain(rotating_equipment=[c1, c2])
        assert dt.evaluate().required_electrical_power_mw == 2.5
