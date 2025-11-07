from datetime import datetime
from unittest.mock import Mock
from uuid import uuid4

import pytest

from libecalc.common.time_utils import Period
from libecalc.common.units import Unit
from libecalc.common.utils.rates import RateType
from libecalc.common.variables import ExpressionEvaluator
from libecalc.domain.infrastructure.emitters.venting_emitter import (
    DirectVentingEmitter,
    EmissionRate,
    OilVentingEmitter,
    OilVolumeRate,
    VentingEmission,
    VentingVolume,
    VentingVolumeEmission,
)
from libecalc.domain.regularity import Regularity
from libecalc.dto.types import ConsumerUserDefinedCategoryType
from libecalc.presentation.yaml.domain.reference_service import ReferenceService
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression
from libecalc.presentation.yaml.mappers.yaml_path import YamlPath
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
    YamlEmissionRateBuilder,
    YamlInstallationBuilder,
    YamlOilVolumeRateBuilder,
    YamlVentingEmissionBuilder,
    YamlVentingEmitterDirectTypeBuilder,
    YamlVentingEmitterOilTypeBuilder,
    YamlVentingVolumeBuilder,
)
from libecalc.presentation.yaml.mappers.component_mapper import EcalcModelMapper, Defaults


class VentingEmitterTestHelper:
    def __init__(self, expression_evaluator_factory):
        self._expression_evaluator_factory = expression_evaluator_factory

    def variables_map(self) -> ExpressionEvaluator:
        return self._expression_evaluator_factory.from_time_vector(
            time_vector=[
                datetime(2000, 1, 1),
                datetime(2001, 1, 1),
                datetime(2002, 1, 1),
                datetime(2003, 1, 1),
                datetime(2004, 1, 1),
            ],
            variables={"TSC1;Methane_rate": self.methane, "TSC1;Oil_rate": self.oil_values},
        )

    @property
    def oil_values(self):
        return [10, 10, 10, 10]

    @property
    def methane(self):
        return [0.005, 1.5, 3, 4]


@pytest.fixture(scope="function")
def venting_emitter_test_helper(expression_evaluator_factory):
    return VentingEmitterTestHelper(expression_evaluator_factory=expression_evaluator_factory)


class TestVentingEmitter:
    def test_venting_emitter(self, venting_emitter_test_helper):
        variables = venting_emitter_test_helper.variables_map()
        regularity = Regularity(
            expression_evaluator=variables,
            target_period=variables.get_period(),
            expression_input={variables.get_period(): 1},
        )

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
            id=uuid4(),
            name=venting_emitter.name,
            component_type=venting_emitter.component_type,
            emitter_type=venting_emitter.type,
            emissions=[
                VentingEmission(
                    name=emission.name,
                    emission_rate=EmissionRate(
                        time_series_expression=TimeSeriesExpression(
                            expression=emission.rate.value, expression_evaluator=variables
                        ),
                        unit=emission.rate.unit.to_unit(),
                        rate_type=emission.rate.type,
                        regularity=regularity,
                    ),
                )
                for emission in venting_emitter.emissions
            ],
            regularity=regularity,
        )

        emission_rate = venting_emitter_dto.get_emissions()["ch4"].to_unit(Unit.TONS_PER_DAY)

        # Two first time steps using emitter_emission_function
        assert emission_rate.values == pytest.approx([5.1e-06, 0.00153, 0.00306, 0.00408])

    def test_venting_emitter_oil_volume(self, venting_emitter_test_helper):
        """
        Check that emissions related to oil loading/storage are correct. These emissions are
        calculated using a factor of input oil rates, i.e. the TYPE set to OIL_VOLUME.
        """
        emitter_name = "venting_emitter"
        emission_factor = 0.1
        regularity_expected = 1.0

        variables = venting_emitter_test_helper.variables_map()

        regularity = Regularity(
            expression_evaluator=variables,
            target_period=variables.get_period(),
            expression_input=regularity_expected,
        )

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
            id=uuid4(),
            name=venting_emitter.name,
            component_type=venting_emitter.component_type,
            emitter_type=venting_emitter.type,
            volume=VentingVolume(
                oil_volume_rate=OilVolumeRate(
                    time_series_expression=TimeSeriesExpression(
                        expression=venting_emitter.volume.rate.value, expression_evaluator=variables
                    ),
                    unit=venting_emitter.volume.rate.unit.to_unit(),
                    rate_type=venting_emitter.volume.rate.type,
                    regularity=regularity,
                ),
                emissions=[
                    VentingVolumeEmission(name=emission.name, emission_factor=emission.emission_factor)
                    for emission in venting_emitter.volume.emissions
                ],
            ),
            regularity=regularity,
        )

        emission_rate = venting_emitter_dto.get_emissions()["ch4"].to_unit(Unit.TONS_PER_DAY)

        expected_result = [
            oil_value * regularity_expected * emission_factor / 1000
            for oil_value in venting_emitter_test_helper.oil_values
        ]

        assert emission_rate.values == expected_result

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

    def test_map_venting_emitter_condition(self, expression_evaluator_factory):
        """
        Test mapping of venting emitter with condition on emission rate.
        """

        time_vector = [datetime(2030, 1, 1), datetime(2031, 1, 1)]
        rate_name = "venting_emitter_rate"
        expression_evaluator = expression_evaluator_factory.from_time_vector(
            time_vector=time_vector, variables={rate_name: [10, 10], "gas_production": [2, 2]}
        )

        mapper = EcalcModelMapper(
            resources=Mock(),
            references=Mock(spec=ReferenceService),
            target_period=Mock(),
            expression_evaluator=expression_evaluator,
            mapping_context=Mock(),
            configuration=Mock(),
        )

        yaml_direct_emitter = YamlVentingEmitterDirectTypeBuilder().with_test_data().validate()
        yaml_direct_emitter.emissions[0].rate.value = rate_name

        # Test with condition that filters out all periods
        yaml_direct_emitter.emissions[0].rate.condition = "gas_production > 4"
        domain_emitter = mapper.map_venting_emitter(
            data=yaml_direct_emitter, id=uuid4(), yaml_path=YamlPath(), defaults=Defaults()
        )
        assert domain_emitter.emissions[0].emission_rate.get_stream_day_values() == [
            0,
            0,
        ]  # Both periods do not meet the condition

        # Test with condition that allows all periods
        yaml_direct_emitter.emissions[0].rate.condition = "gas_production > 1"
        domain_emitter = mapper.map_venting_emitter(
            data=yaml_direct_emitter, id=uuid4(), yaml_path=YamlPath(), defaults=Defaults()
        )
        assert domain_emitter.emissions[0].emission_rate.get_stream_day_values() == [
            10,
            10,
        ]  # Both periods meet the condition
