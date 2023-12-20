import json
import unittest
from datetime import datetime

import yaml
from libecalc import dto
from libecalc.common.units import Unit
from libecalc.core.consumers.pump import Pump
from libecalc.core.models.chart import SingleSpeedChart
from libecalc.core.models.pump import PumpSingleSpeed
from libecalc.domain.stream_conditions import Density, Pressure, Rate, StreamConditions
from libecalc.dto.base import ComponentType
from libecalc.presentation.yaml.yaml_entities import References
from libecalc.presentation.yaml.yaml_types.components.yaml_pump import YamlPump


class TestYamlPump(unittest.TestCase):
    def setUp(self):
        # TODO: Yamlify this as well?
        self.pump_model_references = References(
            models={
                "pump_single_speed": dto.PumpModel(
                    chart=dto.SingleSpeedChart(
                        rate_actual_m3_hour=[100, 200, 300, 400, 500],
                        polytropic_head_joule_per_kg=[1000, 2000, 3000, 4000, 5000],
                        efficiency_fraction=[0.4, 0.5, 0.75, 0.7, 0.6],
                        speed_rpm=0,
                    ),
                    energy_usage_adjustment_constant=0.0,
                    energy_usage_adjustment_factor=1.0,
                    head_margin=0.0,
                )
            },
        )

        self.yaml_pump = YamlPump(
            name="my_pump",
            category="my_category",
            component_type=ComponentType.PUMP_V2,
            energy_usage_model="pump_single_speed",
        )

        self.inlet_stream_condition = StreamConditions(
            id="inlet",
            name="inlet",  # TODO: we should not relay on order of streams in list, but rather require "different types of streams" for now, ie in and out as required
            timestep=datetime(2020, 1, 1),  # TODO: Avoid adding timestep info here, for outer layers
            rate=Rate(
                value=150,
                unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
            ),
            pressure=Pressure(
                value=50,
                unit=Unit.BARA,
            ),
            density=Density(value=1, unit=Unit.KG_SM3),
        )

        self.outlet_stream_condition = StreamConditions(
            id="outlet",
            name="outlet",
            timestep=datetime(2020, 1, 1),
            rate=Rate(
                value=150,
                unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
            ),
            pressure=Pressure(
                value=80,
                unit=Unit.BARA,
            ),
            density=Density(value=1, unit=Unit.KG_SM3),
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

    def test_to_domain(self):
        domain_pump = self.yaml_pump.to_domain_model(
            timestep=datetime(year=2020, month=1, day=1), references=self.pump_model_references
        )

        # NOTE! To get domain model for the whole range of timesteps, we need to call the function for each time step
        expected_domain_pump = Pump(
            "unique pump name",
            pump_model=PumpSingleSpeed(
                pump_chart=SingleSpeedChart.create(
                    speed_rpm=0,  # Speed is ignored...so why set it? .P force users to set it, just for meta?
                    rate_actual_m3_hour=[100, 200, 300, 400, 500],
                    polytropic_head_joule_per_kg=[1000, 2000, 3000, 4000, 5000],
                    efficiency_fraction=[0.4, 0.5, 0.75, 0.7, 0.6],
                ),
                energy_usage_adjustment_constant=0.0,
                energy_usage_adjustment_factor=1.0,
                head_margin=0.0,
            ),
        )

        # TODO: Handle correct comparison - use pydantic, dataclass or make ourselves?
        assert expected_domain_pump == domain_pump

    def test_domain_pump(self):
        domain_pump = self.yaml_pump.to_domain_model(
            timestep=datetime(year=2020, month=1, day=1), references=self.pump_model_references
        )

        max_rate = domain_pump.get_max_rate(
            inlet_stream=self.inlet_stream_condition, target_pressure=Pressure(value=50, unit=Unit.BARA)
        )

        assert max_rate == 12000

        domain_pump.evaluate(streams=[self.inlet_stream_condition, self.outlet_stream_condition])
