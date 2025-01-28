from datetime import datetime

import pytest

from libecalc.common.time_utils import Period
from libecalc.common.units import Unit
from libecalc.common.utils.rates import RateType
from libecalc.common.variables import VariablesMap
from libecalc.core.result.emission import EmissionResult
from libecalc.domain.infrastructure.emitters.venting_emitter import DirectVentingEmitter, OilVentingEmitter
from libecalc.dto.types import ConsumerUserDefinedCategoryType
from libecalc.expression import Expression
from libecalc.presentation.yaml.yaml_types.emitters.yaml_venting_emitter import (
    YamlDirectTypeEmitter,
    YamlOilTypeEmitter,
    YamlVentingEmission,
    YamlVentingType,
    YamlVentingVolume,
    YamlVentingVolumeEmission,
)
from libecalc.presentation.yaml.yaml_types.yaml_stream_conditions import (
    YamlEmissionRate,
    YamlEmissionRateUnits,
    YamlOilRateUnits,
    YamlOilVolumeRate,
)
from libecalc.testing.yaml_builder import (
    YamlVentingEmitterDirectTypeBuilder,
    YamlInstallationBuilder,
    YamlVentingEmitterOilTypeBuilder,
)


class VentingEmitterTestHelper:
    def variables_map(self):
        return VariablesMap(
            variables={"TSC1;Methane_rate": self.methane, "TSC1;Oil_rate": self.oil_values},
            time_vector=[
                datetime(2000, 1, 1),
                datetime(2001, 1, 1),
                datetime(2002, 1, 1),
                datetime(2003, 1, 1),
                datetime(2004, 1, 1),
            ],
        )

    @property
    def oil_values(self):
        return [10, 10, 10, 10]

    @property
    def methane(self):
        return [0.005, 1.5, 3, 4]


@pytest.fixture(scope="module")
def venting_emitter_test_helper():
    return VentingEmitterTestHelper()


class TestVentingEmitter:
    def test_venting_emitter(self, venting_emitter_test_helper):
        variables = venting_emitter_test_helper.variables_map()
        emitter_name = "venting_emitter"

        venting_emitter = YamlDirectTypeEmitter(
            name=emitter_name,
            category=ConsumerUserDefinedCategoryType.COLD_VENTING_FUGITIVE,
            type=YamlVentingType.DIRECT_EMISSION.value,
            emissions=[
                YamlVentingEmission(
                    name="ch4",
                    rate=YamlEmissionRate(
                        value="TSC1;Methane_rate {*} 1.02",
                        unit=YamlEmissionRateUnits.KILO_PER_DAY,
                        type=RateType.STREAM_DAY,
                    ),
                )
            ],
        )

        venting_emitter_dto = DirectVentingEmitter(
            name=venting_emitter.name,
            expression_evaluator=variables,
            component_type=venting_emitter.component_type,
            user_defined_category=venting_emitter.user_defined_category,
            emitter_type=venting_emitter.type,
            emissions=venting_emitter.emissions,
        )

        emission_rate = venting_emitter_dto.get_emissions()["ch4"].to_unit(Unit.TONS_PER_DAY)

        emission_result = {
            venting_emitter.emissions[0].name: EmissionResult(
                name=venting_emitter.emissions[0].name,
                periods=variables.periods,
                rate=emission_rate,
            )
        }
        emissions_ch4 = emission_result["ch4"]

        # Two first time steps using emitter_emission_function
        assert emissions_ch4.rate.values == pytest.approx([5.1e-06, 0.00153, 0.00306, 0.00408])

    def test_venting_emitter_oil_volume(self, venting_emitter_test_helper):
        """
        Check that emissions related to oil loading/storage are correct. These emissions are
        calculated using a factor of input oil rates, i.e. the TYPE set to OIL_VOLUME.
        """
        emitter_name = "venting_emitter"
        emission_factor = 0.1
        regularity_expected = 1.0

        variables = venting_emitter_test_helper.variables_map()

        venting_emitter = YamlOilTypeEmitter(
            name=emitter_name,
            category=ConsumerUserDefinedCategoryType.LOADING,
            type=YamlVentingType.OIL_VOLUME.value,
            volume=YamlVentingVolume(
                rate=YamlOilVolumeRate(
                    value="TSC1;Oil_rate",
                    unit=YamlOilRateUnits.STANDARD_CUBIC_METER_PER_DAY,
                    type=RateType.STREAM_DAY,
                ),
                emissions=[
                    YamlVentingVolumeEmission(
                        name="ch4",
                        emission_factor=emission_factor,
                    )
                ],
            ),
        )

        venting_emitter_dto = OilVentingEmitter(
            name=venting_emitter.name,
            expression_evaluator=variables,
            component_type=venting_emitter.component_type,
            user_defined_category=venting_emitter.user_defined_category,
            emitter_type=venting_emitter.type,
            volume=venting_emitter.volume,
        )

        emission_rate = venting_emitter_dto.get_emissions()["ch4"].to_unit(Unit.TONS_PER_DAY)

        emission_result = {
            venting_emitter.volume.emissions[0].name: EmissionResult(
                name=venting_emitter.volume.emissions[0].name,
                periods=variables.periods,
                rate=emission_rate,
            )
        }
        emissions_ch4 = emission_result["ch4"]

        expected_result = [
            oil_value * regularity_expected * emission_factor / 1000
            for oil_value in venting_emitter_test_helper.oil_values
        ]

        assert emissions_ch4.rate.values == expected_result

    def test_no_emissions_direct(self):
        """
        Check that error message is given if no emissions are specified for TYPE DIRECT_EMISSION.
        """

        with pytest.raises(ValueError) as exc:
            YamlDirectTypeEmitter(
                name="venting_emitter",
                category=ConsumerUserDefinedCategoryType.COLD_VENTING_FUGITIVE,
                type=YamlVentingType.DIRECT_EMISSION.name,
            )

        assert "1 validation error for VentingEmitter\nEMISSIONS\n  Field required" in str(exc.value)

    def test_no_volume_oil(self):
        """
        Check that error message is given if no volume is specified for TYPE OIL_VOLUME.
        """

        with pytest.raises(ValueError) as exc:
            YamlOilTypeEmitter(
                name="venting_emitter",
                category=ConsumerUserDefinedCategoryType.COLD_VENTING_FUGITIVE,
                type=YamlVentingType.OIL_VOLUME.name,
            )

        assert "1 validation error for VentingEmitter\nVOLUME\n  Field required" in str(exc.value)

    def test_venting_emitters_direct_uppercase_emissions_name(self):
        """
        Check emission names are case-insensitive for venting emitters of type DIRECT_EMISSION.
        """

        emission_rates = [10, 5]

        venting_emitter = (
            YamlVentingEmitterDirectTypeBuilder()
            .with_name("Venting emitter 1")
            .with_category(ConsumerUserDefinedCategoryType.COLD_VENTING_FUGITIVE)
            .with_emission_names_rates_units_and_types(
                names=["CO2", "nmVOC"],
                rates=emission_rates,
                units=[YamlEmissionRateUnits.KILO_PER_DAY, YamlEmissionRateUnits.KILO_PER_DAY],
                rate_types=[RateType.STREAM_DAY, RateType.STREAM_DAY],
            )
        ).validate()

        installation = (
            YamlInstallationBuilder().with_name("Installation").with_venting_emitters([venting_emitter])
        ).validate()

        assert installation.venting_emitters[0].emissions[0].name == "co2"
        assert installation.venting_emitters[0].emissions[1].name == "nmvoc"

    def test_venting_emitters_volume_uppercase_emissions_name(self):
        """
        Check emission names are case-insensitive for venting emitters of type OIL_VOLUME.
        """

        emission_factors = [0.1, 0.1]
        oil_rate = 100

        venting_emitter = (
            YamlVentingEmitterOilTypeBuilder()
            .with_name("Venting emitter 1")
            .with_category(ConsumerUserDefinedCategoryType.LOADING)
            .with_rate_and_emission_names_and_factors(
                rate=oil_rate,
                names=["CO2", "nmVOC"],
                factors=emission_factors,
                unit=YamlOilRateUnits.STANDARD_CUBIC_METER_PER_DAY,
                rate_type=RateType.CALENDAR_DAY,
            )
        ).validate()

        installation = (
            YamlInstallationBuilder().with_name("Installation").with_venting_emitters([venting_emitter])
        ).validate()

        assert installation.venting_emitters[0].volume.emissions[0].name == "co2"
        assert installation.venting_emitters[0].volume.emissions[1].name == "nmvoc"
