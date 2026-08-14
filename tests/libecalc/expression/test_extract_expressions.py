from pydantic import BaseModel

from libecalc.expression.extract_expressions import extract_expression_references
from libecalc.presentation.yaml.yaml_types.components.yaml_asset import YamlDefinitions
from libecalc.presentation.yaml.yaml_types.process.yaml_fluid_definitions import YamlFluidComposition
from libecalc.presentation.yaml.yaml_types.process.yaml_process_simulation import YamlPumpProcessInlet
from libecalc.presentation.yaml.yaml_types.process.yaml_process_units import (
    YamlPressureDropperDefinition,
    YamlTemperatureSetterDefinition,
)
from libecalc.presentation.yaml.yaml_types.process.yaml_stream_distribution import YamlCommonStreamSetting
from libecalc.presentation.yaml.yaml_types.streams.yaml_inlet_stream import (
    YamlInletStream,
    YamlInletStreamRate,
)
from libecalc.testing.process_builders import YamlCompositionFluidDefinitionBuilder


class TestExtractExpressionReferences:
    def test_single_expression_field(self):
        model = YamlPressureDropperDefinition(type="PRESSURE_DROPPER", pressure_drop="SIM1;DP")
        assert extract_expression_references(model) == {"SIM1;DP"}

    def test_numeric_expression_has_no_references(self):
        model = YamlPressureDropperDefinition(type="PRESSURE_DROPPER", pressure_drop=5.0)
        assert extract_expression_references(model) == set()

    def test_expression_with_arithmetic(self):
        model = YamlTemperatureSetterDefinition(type="TEMPERATURE_SETTER", temperature="SIM1;TEMP {*} 1.1 {+} 5")
        assert extract_expression_references(model) == {"SIM1;TEMP"}

    def test_multiple_references_in_one_expression(self):
        model = YamlPressureDropperDefinition(type="PRESSURE_DROPPER", pressure_drop="SIM1;DP {+} SIM2;DP_EXTRA")
        assert extract_expression_references(model) == {"SIM1;DP", "SIM2;DP_EXTRA"}

    def test_nested_pydantic_model(self):
        stream = YamlInletStream(
            name="test_stream",
            fluid="my_fluid",
            temperature="SIM1;TEMP_IN",
            pressure="SIM1;PRESSURE_IN",
            rate=YamlInletStreamRate(
                value="SIM1;OIL_PROD",
                unit="SM3_PER_DAY",
                type="STREAM_DAY",
            ),
        )
        refs = extract_expression_references(stream)
        assert refs == {"SIM1;TEMP_IN", "SIM1;PRESSURE_IN", "SIM1;OIL_PROD"}

    def test_optional_expression_field(self):
        """condition is Optional[YamlExpressionType]."""
        rate = YamlInletStreamRate(
            value="SIM1;RATE",
            unit="SM3_PER_DAY",
            type="STREAM_DAY",
            condition="SIM1;IS_ACTIVE",
        )
        refs = extract_expression_references(rate)
        assert refs == {"SIM1;RATE", "SIM1;IS_ACTIVE"}

    def test_optional_expression_field_none(self):
        rate = YamlInletStreamRate(
            value="SIM1;RATE",
            unit="SM3_PER_DAY",
            type="STREAM_DAY",
        )
        refs = extract_expression_references(rate)
        assert refs == {"SIM1;RATE"}

    def test_list_of_expressions(self):
        setting = YamlCommonStreamSetting(rate_fractions=["SIM1;FRAC_A", "SIM1;FRAC_B", 0.5])
        refs = extract_expression_references(setting)
        assert refs == {"SIM1;FRAC_A", "SIM1;FRAC_B"}

    def test_list_of_conditions(self):
        rate = YamlInletStreamRate(
            value="SIM1;RATE",
            unit="SM3_PER_DAY",
            type="STREAM_DAY",
            conditions=["SIM1;COND_A", "SIM1;COND_B"],
        )
        refs = extract_expression_references(rate)
        assert refs == {"SIM1;RATE", "SIM1;COND_A", "SIM1;COND_B"}

    def test_multiple_expression_fields(self):
        inlet = YamlPumpProcessInlet(rate="SIM1;RATE", pressure="SIM1;P_IN", density="SIM1;RHO")
        refs = extract_expression_references(inlet)
        assert refs == {"SIM1;RATE", "SIM1;P_IN", "SIM1;RHO"}

    def test_model_with_no_expressions(self):
        """A model with no expression fields should return empty set."""

        class PlainModel(BaseModel):
            name: str
            value: int

        model = PlainModel(name="test", value=42)
        assert extract_expression_references(model) == set()

    def test_var_references(self):
        model = YamlPressureDropperDefinition(type="PRESSURE_DROPPER", pressure_drop="$var.regularity {*} SIM1;DP")
        refs = extract_expression_references(model)
        assert refs == {"$var.regularity", "SIM1;DP"}

    def test_dict_field_with_expression_values(self):
        """dict[str, YamlExpressionType] should be detected and extracted."""
        from libecalc.presentation.yaml.yaml_types.components.yaml_expression_type import YamlExpressionType

        class ModelWithDict(BaseModel):
            expressions: dict[str, YamlExpressionType]

        model = ModelWithDict(expressions={"a": "SIM1;RATE", "b": "SIM2;PRESSURE"})
        refs = extract_expression_references(model)
        assert refs == {"SIM1;RATE", "SIM2;PRESSURE"}

    def test_extracts_references_from_fluid_definitions(self):
        """Fluid composition expressions are included when extracting dependencies from definitions."""
        fluid_definition = (
            YamlCompositionFluidDefinitionBuilder()
            .with_composition(
                YamlFluidComposition(
                    methane="FEED;METHANE",
                    ethane="FEED;ETHANE {*} 0.5",
                )
            )
            .validate()
        )
        definitions = YamlDefinitions(
            fluids={"feed_gas": fluid_definition},
        )

        assert extract_expression_references(definitions) == {
            "FEED;METHANE",
            "FEED;ETHANE",
        }
