import pytest

from libecalc.common.errors.exceptions import IllegalStateException
from libecalc.common.units import UnitConstants
from libecalc.domain.process.compressor.core.train.utils.common import (
    CompressorOutletCalculationError,
    calculate_asv_corrected_rate,
    calculate_outlet_pressure_and_stream,
    calculate_power_in_megawatt,
)
from libecalc.domain.process.compressor.core.train.utils.enthalpy_calculations import (
    _calculate_polytropic_exponent_expression_n_minus_1_over_n,
    calculate_outlet_pressure_campbell,
)
from libecalc.domain.process.entities.process_units.legacy_compressor import legacy_compressor
from libecalc.domain.process.entities.process_units.legacy_compressor.legacy_compressor import (
    LegacyCompressor,
    OperationalPoint,
)
from libecalc.domain.process.value_objects.chart.chart_area_flag import ChartAreaFlag
from libecalc.process.fluid_stream.fluid import Fluid
from libecalc.process.fluid_stream.fluid_model import EoSModel, FluidComposition, FluidModel
from libecalc.process.fluid_stream.fluid_properties import FluidProperties
from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.shaft import SingleSpeedShaft


def test_calculate_polytropic_exponent_expression(
    test_data_compressor_train_common_shaft,
):
    for kappa, polytropic_efficiency in zip(
        test_data_compressor_train_common_shaft.kappa_values,
        test_data_compressor_train_common_shaft.polytropic_efficiency_values,
    ):
        assert _calculate_polytropic_exponent_expression_n_minus_1_over_n(
            kappa=kappa, polytropic_efficiency=polytropic_efficiency
        ) == (kappa - 1.0) / (kappa * polytropic_efficiency)


def test_calculate_outlet_pressure_campbell(
    test_data_compressor_train_common_shaft,
):
    # Use only the first element of each attribute of the fixture
    kappa = float(test_data_compressor_train_common_shaft.kappa_values[0])
    polytropic_efficiency = float(test_data_compressor_train_common_shaft.polytropic_efficiency_values[0])
    polytropic_head_fluid_Joule_per_kg = float(
        test_data_compressor_train_common_shaft.polytropic_head_fluid_Joule_per_kg_values[0]
    )
    molar_mass = float(test_data_compressor_train_common_shaft.molar_mass_values[0])
    z_inlet = float(test_data_compressor_train_common_shaft.z_inlet_values[0])
    inlet_temperature_K = float(test_data_compressor_train_common_shaft.inlet_temperature_K_values[0])
    inlet_pressure_bara = float(test_data_compressor_train_common_shaft.inlet_pressure_bara_values[0])

    polytropic_exponent_n_over_n_minus_1 = 1.0 / _calculate_polytropic_exponent_expression_n_minus_1_over_n(
        kappa=kappa,
        polytropic_efficiency=polytropic_efficiency,
    )
    pressure_fraction = (
        1.0
        + polytropic_head_fluid_Joule_per_kg
        / polytropic_exponent_n_over_n_minus_1
        * molar_mass
        / (z_inlet * UnitConstants.GAS_CONSTANT * inlet_temperature_K)
    ) ** (polytropic_exponent_n_over_n_minus_1)
    expected_outlet_pressure = inlet_pressure_bara * pressure_fraction

    result = calculate_outlet_pressure_campbell(
        kappa=kappa,
        polytropic_efficiency=polytropic_efficiency,
        inlet_pressure_bara=inlet_pressure_bara,
        molar_mass=molar_mass,
        z_inlet=z_inlet,
        inlet_temperature_K=inlet_temperature_K,
        polytropic_head_fluid_Joule_per_kg=polytropic_head_fluid_Joule_per_kg,
    )
    assert result == pytest.approx(expected_outlet_pressure)


def test_calculate_outlet_pressure_and_stream_rejects_invalid_ph_result():
    fluid_model = FluidModel(
        composition=FluidComposition(methane=1.0),
        eos_model=EoSModel.PR,
    )
    inlet_properties = FluidProperties(
        temperature_kelvin=300.0,
        pressure_bara=20.0,
        density=30.0,
        enthalpy_joule_per_kg=1000.0,
        z=0.9,
        kappa=1.3,
        vapor_fraction_molar=1.0,
        molar_mass=0.016,
        standard_density=0.7,
    )
    inlet_stream = FluidStream(
        fluid=Fluid(fluid_model=fluid_model, properties=inlet_properties),
        mass_rate_kg_per_h=1.0,
    )

    class InvalidPhFlashService:
        temperature_guesses: list[float | None]

        def __init__(self) -> None:
            self.temperature_guesses = []

        def flash_ph(
            self,
            fluid_model: FluidModel,
            pressure_bara: float,
            target_enthalpy: float,
            temperature_guess_kelvin: float | None = None,
        ) -> FluidProperties:
            self.temperature_guesses.append(temperature_guess_kelvin)
            return FluidProperties(
                temperature_kelvin=288.15,
                pressure_bara=pressure_bara,
                density=100.0,
                enthalpy_joule_per_kg=target_enthalpy,
                z=0.6,
                kappa=float("nan"),
                vapor_fraction_molar=0.3,
                molar_mass=0.016,
                standard_density=0.7,
            )

    fluid_service = InvalidPhFlashService()

    with pytest.raises(CompressorOutletCalculationError, match="kappa"):
        calculate_outlet_pressure_and_stream(
            polytropic_efficiency=0.75,
            polytropic_head_joule_per_kg=10_000.0,
            inlet_stream=inlet_stream,
            fluid_service=fluid_service,  # type: ignore[arg-type]
        )

    assert fluid_service.temperature_guesses == [inlet_stream.temperature_kelvin]


def test_invalid_compressor_chart_point_returns_inlet_when_outlet_calculation_fails(
    monkeypatch, single_speed_chart_data
):
    fluid_model = FluidModel(
        composition=FluidComposition(methane=1.0),
        eos_model=EoSModel.PR,
    )
    inlet_stream = FluidStream(
        fluid=Fluid(
            fluid_model=fluid_model,
            properties=FluidProperties(
                temperature_kelvin=300.0,
                pressure_bara=20.0,
                density=30.0,
                enthalpy_joule_per_kg=1000.0,
                z=0.9,
                kappa=1.3,
                vapor_fraction_molar=1.0,
                molar_mass=0.016,
                standard_density=0.7,
            ),
        ),
        mass_rate_kg_per_h=1.0,
    )
    compressor = LegacyCompressor(
        compressor_chart=single_speed_chart_data,
        fluid_service=object(),  # type: ignore[arg-type]
        shaft=SingleSpeedShaft(),
    )
    compressor.set_rate_before_asv(rate_before_asv_m3_per_h=10_000.0)

    def set_invalid_operational_point(actual_rate_m3_per_h_including_asv: float) -> None:
        compressor._operational_point = OperationalPoint(
            actual_rate_m3_per_h=actual_rate_m3_per_h_including_asv,
            polytropic_head_joule_per_kg=100_000.0,
            polytropic_efficiency=0.75,
            is_valid=False,
        )
        compressor._chart_area_flag = ChartAreaFlag.ABOVE_MAXIMUM_FLOW_RATE

    def fail_outlet_calculation(**kwargs) -> FluidStream:
        raise CompressorOutletCalculationError("thermodynamic outlet calculation failed")

    monkeypatch.setattr(compressor, "set_chart_area_flag_and_operational_point", set_invalid_operational_point)
    monkeypatch.setattr(legacy_compressor, "calculate_outlet_pressure_and_stream", fail_outlet_calculation)

    assert compressor.compress(inlet_stream) is inlet_stream
    assert compressor.operational_point is not None
    assert not compressor.operational_point.is_valid
    assert compressor.chart_area_flag == ChartAreaFlag.ABOVE_MAXIMUM_FLOW_RATE


def test_invalid_compressor_chart_point_does_not_swallow_unrelated_illegal_state(monkeypatch, single_speed_chart_data):
    fluid_model = FluidModel(
        composition=FluidComposition(methane=1.0),
        eos_model=EoSModel.PR,
    )
    inlet_stream = FluidStream(
        fluid=Fluid(
            fluid_model=fluid_model,
            properties=FluidProperties(
                temperature_kelvin=300.0,
                pressure_bara=20.0,
                density=30.0,
                enthalpy_joule_per_kg=1000.0,
                z=0.9,
                kappa=1.3,
                vapor_fraction_molar=1.0,
                molar_mass=0.016,
                standard_density=0.7,
            ),
        ),
        mass_rate_kg_per_h=1.0,
    )
    compressor = LegacyCompressor(
        compressor_chart=single_speed_chart_data,
        fluid_service=object(),  # type: ignore[arg-type]
        shaft=SingleSpeedShaft(),
    )
    compressor.set_rate_before_asv(rate_before_asv_m3_per_h=10_000.0)

    def set_invalid_operational_point(actual_rate_m3_per_h_including_asv: float) -> None:
        compressor._operational_point = OperationalPoint(
            actual_rate_m3_per_h=actual_rate_m3_per_h_including_asv,
            polytropic_head_joule_per_kg=100_000.0,
            polytropic_efficiency=0.75,
            is_valid=False,
        )
        compressor._chart_area_flag = ChartAreaFlag.ABOVE_MAXIMUM_FLOW_RATE

    def fail_outlet_calculation(**kwargs) -> FluidStream:
        raise IllegalStateException("unrelated illegal state")

    monkeypatch.setattr(compressor, "set_chart_area_flag_and_operational_point", set_invalid_operational_point)
    monkeypatch.setattr(legacy_compressor, "calculate_outlet_pressure_and_stream", fail_outlet_calculation)

    with pytest.raises(IllegalStateException, match="unrelated illegal state"):
        compressor.compress(inlet_stream)


def test_calculate_asv_corrected_rate():
    # Test when actual rate is larger than minimum
    actual_rate_m3_per_hour = 5
    density_kg_per_m3 = 10
    mass_rate_kg_per_hour = actual_rate_m3_per_hour * density_kg_per_m3
    (
        actual_rate_asv_corrected_m3_per_hour,
        mass_rate_asv_corrected_kg_per_hour,
    ) = calculate_asv_corrected_rate(
        actual_rate_m3_per_hour=actual_rate_m3_per_hour,
        minimum_actual_rate_m3_per_hour=3,
        density_kg_per_m3=density_kg_per_m3,
    )
    # Expect no change to rate du to asv
    assert actual_rate_asv_corrected_m3_per_hour == actual_rate_m3_per_hour
    assert mass_rate_asv_corrected_kg_per_hour == mass_rate_kg_per_hour

    # Test when actual rate is smaller than minimum
    minimum_actual_rate_m3_per_hour = 6
    (
        actual_rate_asv_corrected_m3_per_hour,
        mass_rate_asv_corrected_kg_per_hour,
    ) = calculate_asv_corrected_rate(
        actual_rate_m3_per_hour=actual_rate_m3_per_hour,
        minimum_actual_rate_m3_per_hour=minimum_actual_rate_m3_per_hour,
        density_kg_per_m3=density_kg_per_m3,
    )
    assert actual_rate_asv_corrected_m3_per_hour == minimum_actual_rate_m3_per_hour
    assert mass_rate_asv_corrected_kg_per_hour == minimum_actual_rate_m3_per_hour * density_kg_per_m3


def test_calculate_power_in_megawatt():
    mass_rate_kg_per_hour = 5
    enthalpy_change_joule_per_kg = 10.0
    power_megawatt = calculate_power_in_megawatt(
        mass_rate_kg_per_hour=mass_rate_kg_per_hour,
        enthalpy_change_joule_per_kg=enthalpy_change_joule_per_kg,
    )
    assert power_megawatt == (
        enthalpy_change_joule_per_kg
        * mass_rate_kg_per_hour
        / UnitConstants.SECONDS_PER_HOUR
        * UnitConstants.WATT_TO_MEGAWATT
    )
