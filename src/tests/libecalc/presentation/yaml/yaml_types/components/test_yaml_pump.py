import json
import unittest

import yaml
from libecalc.dto.base import ComponentType
from libecalc.presentation.yaml.yaml_types.components.yaml_pump import YamlPump


class TestYamlPump(unittest.TestCase):
    def setUp(self):
        self.yaml_pump = YamlPump(
            name="my_pump",
            category="my_category",
            component_type=ComponentType.PUMP_V2,
            energy_usage_model="pump_single_speed",
        )

    def test_serialize(self):
        expected_serialized = {
            "name": "my_pump",
            "category": "my_category",
            "component_type": "PUMP@v2",
            "energy_usage_model": "pump_single_speed",
        }
        serialized = self.yaml_pump.json()
        assert json.dumps(expected_serialized) == serialized

    def test_deserialize(self):
        # objectify?
        serialized_dict = {
            "name": "my_pump",
            "category": "my_category",
            "component_type": "PUMP@v2",
            "energy_usage_model": "pump_single_speed",
        }
        assert self.yaml_pump == YamlPump.parse_obj(serialized_dict)

    def test_generate_json_schema(self):
        schema = YamlPump.schema(by_alias=True)
        YamlPump.schema_json()
        expected_schema_dict = {
            "title": "Pump",
            "type": "object",
            "properties": {
                "NAME": {"title": "NAME", "description": "Consumer name", "type": "string"},
                "CATEGORY": {"title": "CATEGORY", "description": "User defined category", "type": "string"},
                "TYPE": {
                    "title": "TYPE",
                    "description": "The type of the component",
                    "enum": ["PUMP@v2"],
                    "type": "string",
                },
                "ENERGY_USAGE_MODEL": {
                    "title": "Energy Usage Model",
                    "anyOf": [{"type": "string"}, {"type": "object", "additionalProperties": {"type": "string"}}],
                },
            },
            "required": ["NAME", "TYPE", "ENERGY_USAGE_MODEL"],
            "additionalProperties": False,
        }

        assert expected_schema_dict == schema

    def test_generate_yaml(self):
        # TODO: We need to have a special yaml converter - if we want - that can also take an uninitizlied yaml class
        # Might not use
        expected_yaml = """category: my_category
component_type: !!python/object/apply:libecalc.dto.base.ComponentType
- PUMP@v2
energy_usage_model: pump_single_speed
name: my_pump
"""
        generated_yaml = yaml.dump(self.yaml_pump.dict())
        assert expected_yaml == generated_yaml

    # - NAME: pump_single_speed
    # FILE: pumpchart.csv
    # TYPE: PUMP_CHART_SINGLE_SPEED
    # UNITS:
    # EFFICIENCY: FRACTION
    # HEAD: M
    # RATE: AM3_PER_HOUR

    # energy_usage_model: YamlTemporalModel[str]

    #
    # def to_dto(
    #     self,
    #     consumes: ConsumptionType,
    #     regularity: Dict[datetime, Expression],
    #     target_period: Period,
    #     references: References,
    #     category: str,
    #     fuel: Optional[Dict[datetime, dto.types.FuelType]],
    # ):
    #     return PumpComponent(
    #         consumes=consumes,
    #         regularity=regularity,
    #         name=self.name,
    #         user_defined_category=define_time_model_for_period(self.category or category, target_period=target_period),
    #         fuel=fuel,
    #         energy_usage_model={
    #             timestep: resolve_reference(
    #                 value=reference,
    #                 references=references.models,
    #             )
    #             for timestep, reference in define_time_model_for_period(
    #                 self.energy_usage_model, target_period=target_period
    #             ).items()
    #         },
    #     )
