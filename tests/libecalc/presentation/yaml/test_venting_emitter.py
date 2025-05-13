from datetime import datetime

import pytest

from libecalc.common.units import Unit
from libecalc.common.utils.rates import RateType
from libecalc.common.variables import VariablesMap
from libecalc.core.result.emission import EmissionResult
from libecalc.domain.infrastructure.emitters.venting_emitter import (
    DirectVentingEmitter,
    OilVentingEmitter,
    VentingVolume,
    OilVolumeRate,
    VentingVolumeEmission,
    VentingEmission,
    EmissionRate,
)
from libecalc.domain.regularity import Regularity
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
    YamlVentingVolumeBuilder,
    YamlOilVolumeRateBuilder,
    YamlEmissionRateBuilder,
    YamlVentingEmissionBuilder,
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
        regularity = {variables.period: Expression.setup_from_expression(value=1)}

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
            emissions=[
                VentingEmission(
                    name=emission.name,
                    emission_rate=EmissionRate(
                        value=emission.rate.value,
                        unit=emission.rate.unit.to_unit(),
                        rate_type=emission.rate.type,
                    ),
                )
                for emission in venting_emitter.emissions
            ],
            regularity=regularity,
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
            volume=VentingVolume(
                oil_volume_rate=OilVolumeRate(
                    value=venting_emitter.volume.rate.value,
                    unit=venting_emitter.volume.rate.unit.to_unit(),
                    rate_type=venting_emitter.volume.rate.type,
                ),
                emissions=[
                    VentingVolumeEmission(name=emission.name, emission_factor=emission.emission_factor)
                    for emission in venting_emitter.volume.emissions
                ],
            ),
            regularity=Regularity.create(expression_evaluator=variables, expression_input=regularity_expected),
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

    def test_yaml_direct_type_emitter_with_condition(self):
        rate = YamlEmissionRateBuilder().with_test_data().with_condition("x > 5").validate()
        emissions = [YamlVentingEmissionBuilder().with_test_data().with_rate(rate).validate()]
        emitter = YamlVentingEmitterDirectTypeBuilder().with_test_data().with_emissions(emissions).validate()

        # Assertions
        assert emitter.emissions[0].rate.condition == "x > 5"
        assert emitter.emissions[0].rate.conditions is None

    def test_yaml_direct_type_emitter_with_conditions(self):
        rate = YamlEmissionRateBuilder().with_test_data().with_conditions(["z > 0", "w < 50"]).validate()
        emissions = [YamlVentingEmissionBuilder().with_test_data().with_rate(rate).validate()]
        emitter = YamlVentingEmitterDirectTypeBuilder().with_test_data().with_emissions(emissions).validate()

        # Assertions
        assert emitter.emissions[0].rate.condition is None
        assert emitter.emissions[0].rate.conditions == ["z > 0", "w < 50"]

    def test_yaml_oil_type_emitter_with_condition(self):
        rate = YamlOilVolumeRateBuilder().with_test_data().with_condition("x > 5").validate()
        volume = YamlVentingVolumeBuilder().with_test_data().with_rate(rate).validate()
        emitter = YamlVentingEmitterOilTypeBuilder().with_test_data().with_volume(volume).validate()

        # Assertions
        assert emitter.volume.rate.condition == "x > 5"
        assert emitter.volume.rate.conditions is None

    def test_yaml_oil_type_emitter_with_conditions(self):
        rate = YamlOilVolumeRateBuilder().with_test_data().with_conditions(["z > 0", "w < 50"]).validate()
        volume = YamlVentingVolumeBuilder().with_test_data().with_rate(rate).validate()
        emitter = YamlVentingEmitterOilTypeBuilder().with_test_data().with_volume(volume).validate()

        # Assertions
        assert emitter.volume.rate.condition is None
        assert emitter.volume.rate.conditions == ["z > 0", "w < 50"]
