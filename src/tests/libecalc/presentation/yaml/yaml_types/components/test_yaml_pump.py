import json
import unittest

import yaml
from libecalc.core.consumers.pump import Pump
from libecalc.core.models.chart import SingleSpeedChart
from libecalc.core.models.pump import PumpSingleSpeed
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

    def test_to_domain(self):
        # TODO: We now also need
        #  consumption type       for network and produce/subscribe
        #         regularity   from installation, to convert to stream day...
        #         target_period: Period,  # get correct model(s) for period...but skip, as we will not let core know about this
        #         references: References,  # need to resolve, but that should be handled "before"? or here? handle "before"
        #         category: str,  # meta ... just keep here ...
        #         fuel: Optional[Dict[datetime, dto.types.FuelType]], from installation...just add the values ... or is this for emission only, skip?
        self.yaml_pump.to_domain()

        # or pump = PumpFactory.create(id=name, chart=single_speed_chart)
        # or pump = PumpFactory.create(id=name, data=single_speed_chart)

        # for each timestep, create a pump?
        domain_pump = Pump(
            "unique pump name",
            pump_model=PumpSingleSpeed(
                pump_chart=SingleSpeedChart.create(
                    speed_rpm=0,  # Speed is ignored...so why the hell set it? .P force users to set it, just for meta?
                    rate_actual_m3_hour=[100, 200, 300, 400, 500],
                    polytropic_head_joule_per_kg=[1000, 2000, 3000, 4000, 5000],
                    efficiency_fraction=[0.4, 0.5, 0.75, 0.7, 0.6],
                ),
                energy_usage_adjustment_constant=0.0,
                energy_usage_adjustment_factor=1.0,
                head_margin=0.0,
            ),
        )

        energy = domain_pump.simulate(stream)  # iterate, timesteps, for each rate value
        EmissionCalculator(energy, fuel)  # fuel is actually, emission factors etc given the fuel (combinations) used.
        # set category directly?
        energy.to_calendar_day(regularity=regularity)

        # TODO: Add a pump for a period of 30 years
        # initially 1 type, different rates
        # then change charts...?
        #
        # TODO: conversion of expressions? in app layer? not in domain model ...
