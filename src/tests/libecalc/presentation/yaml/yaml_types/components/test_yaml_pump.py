import json
import unittest
from datetime import datetime

import numpy as np
import yaml
from libecalc import dto
from libecalc.common.units import Unit
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
                        speed_rpm=0,  # Speed is ignored...so why set it? .P force users to set it, just for meta?
                        rate_actual_m3_hour=[200, 500, 1000, 1300, 1500],
                        polytropic_head_joule_per_kg=[
                            Unit.POLYTROPIC_HEAD_METER_LIQUID_COLUMN.to(Unit.POLYTROPIC_HEAD_JOULE_PER_KG)(x)
                            for x in [3000.0, 2500.0, 2400.0, 2000.0, 1900.0]
                        ],
                        efficiency_fraction=[0.4, 0.5, 0.6, 0.7, 0.8],
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
                value=28750,
                unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
            ),
            pressure=Pressure(
                value=3,
                unit=Unit.BARA,
            ),
            density=Density(value=1000, unit=Unit.KG_SM3),
        )

        self.outlet_stream_condition = StreamConditions(
            id="outlet",
            name="outlet",
            timestep=datetime(2020, 1, 1),
            rate=Rate(
                value=28750,
                unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
            ),
            pressure=Pressure(
                value=200,
                unit=Unit.BARA,
            ),
            density=Density(value=1000, unit=Unit.KG_SM3),
        )

    def test_serialize(self):
        expected_serialized = {
            "name": "my_pump",
            "category": "my_category",
            "component_type": "PUMP@v2",
            "energy_usage_model": "pump_single_speed",
            "stream_conditions": None,
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
            "additionalProperties": False,
            "definitions": {
                "Unit": {
                    "description": "A very simple unit registry to " "convert between common eCalc units.",
                    "enum": [
                        "N/A",
                        "kg/BOE",
                        "kg/Sm3",
                        "kg/m3",
                        "Sm3",
                        "BOE",
                        "t/d",
                        "t",
                        "kg/d",
                        "kg/h",
                        "kg",
                        "L/d",
                        "L",
                        "MWd",
                        "GWh",
                        "MW",
                        "Y",
                        "bara",
                        "kPa",
                        "Pa",
                        "C",
                        "K",
                        "frac",
                        "%",
                        "kJ/kg",
                        "J/kg",
                        "N.m/kg",
                        "Am3/h",
                        "Sm3/d",
                        "RPM",
                    ],
                    "title": "Unit",
                    "type": "string",
                },
                "YamlDensity": {
                    "additionalProperties": False,
                    "properties": {
                        "UNIT": {"allOf": [{"$ref": "#/definitions/Unit"}], "default": "kg/Sm3"},
                        "VALUE": {
                            "anyOf": [{"type": "string"}, {"type": "number"}, {"type": "integer"}],
                            "title": "Value",
                        },
                    },
                    "required": ["VALUE"],
                    "title": "Density",
                    "type": "object",
                },
                "YamlPressure": {
                    "additionalProperties": False,
                    "properties": {
                        "UNIT": {"allOf": [{"$ref": "#/definitions/Unit"}], "default": "bara"},
                        "VALUE": {
                            "anyOf": [{"type": "string"}, {"type": "number"}, {"type": "integer"}],
                            "title": "Value",
                        },
                    },
                    "required": ["VALUE"],
                    "title": "Pressure",
                    "type": "object",
                },
                "YamlRate": {
                    "additionalProperties": False,
                    "properties": {
                        "UNIT": {"allOf": [{"$ref": "#/definitions/Unit"}], "default": "Sm3/d"},
                        "VALUE": {
                            "anyOf": [{"type": "string"}, {"type": "number"}, {"type": "integer"}],
                            "title": "Value",
                        },
                    },
                    "required": ["VALUE"],
                    "title": "Rate",
                    "type": "object",
                },
                "YamlStreamConditions": {
                    "additionalProperties": False,
                    "properties": {
                        "FLUID_DENSITY": {
                            "allOf": [{"$ref": "#/definitions/YamlDensity"}],
                            "description": "The " "fluid " "density...",
                            "title": "Fluid " "density",
                        },
                        "PRESSURE": {
                            "allOf": [{"$ref": "#/definitions/YamlPressure"}],
                            "description": "Pressure..",
                            "title": "Pressure",
                        },
                        "RATE": {
                            "allOf": [{"$ref": "#/definitions/YamlRate"}],
                            "description": "Rate...",
                            "title": "Rate",
                        },
                        "TEMPERATURE": {
                            "allOf": [{"$ref": "#/definitions/YamlTemperature"}],
                            "description": "Temperature...",
                            "title": "Temperature",
                        },
                    },
                    "title": "Stream",
                    "type": "object",
                },
                "YamlTemperature": {
                    "additionalProperties": False,
                    "properties": {
                        "UNIT": {"allOf": [{"$ref": "#/definitions/Unit"}], "default": "K"},
                        "VALUE": {
                            "anyOf": [{"type": "string"}, {"type": "number"}, {"type": "integer"}],
                            "title": "Value",
                        },
                    },
                    "required": ["VALUE"],
                    "title": "Temperature",
                    "type": "object",
                },
            },
            "description": "V2 only.\n"
            "\n"
            "This DTO represents the pump in the yaml, and must therefore "
            "be a 1:1 to the yaml for a pump.\n"
            "\n"
            "It currently contains a simple string and dict mapping to the "
            "values in the YAML, and must therefore be parsed and resolved "
            "before being used.\n"
            "We may want to add the parsing and resolving here, to avoid "
            "an additional layer for parsing and resolving ...",
            "properties": {
                "CATEGORY": {"description": "User defined category", "title": "CATEGORY", "type": "string"},
                "ENERGY_USAGE_MODEL": {
                    "anyOf": [{"type": "string"}, {"additionalProperties": {"type": "string"}, "type": "object"}],
                    "title": "Energy Usage Model",
                },
                "NAME": {"description": "Consumer name", "title": "NAME", "type": "string"},
                "STREAM_CONDITIONS": {
                    "additionalProperties": {"$ref": "#/definitions/YamlStreamConditions"},
                    "title": "Stream Conditions",
                    "type": "object",
                },
                "TYPE": {
                    "description": "The type of the component",
                    "enum": ["PUMP@v2"],
                    "title": "TYPE",
                    "type": "string",
                },
            },
            "required": ["NAME", "TYPE", "ENERGY_USAGE_MODEL"],
            "title": "Pump",
            "type": "object",
        }

        assert expected_schema_dict == schema

    def test_generate_yaml(self):
        # TODO: We need to have a special yaml converter - if we want - that can also take an uninitialized yaml class
        # We also want to create a proper yaml, and create a separate yaml for the reference etc ...
        # This basically shows that we are not there...yet...
        # Might not use
        expected_yaml = """category: my_category
component_type: !!python/object/apply:libecalc.dto.base.ComponentType
- PUMP@v2
energy_usage_model: pump_single_speed
name: my_pump
stream_conditions: null
"""
        generated_yaml = yaml.dump(self.yaml_pump.dict())
        assert expected_yaml == generated_yaml

    def test_domain_pump(self):
        domain_pump = self.yaml_pump.to_domain_model(
            timestep=datetime(year=2020, month=1, day=1), references=self.pump_model_references
        )

        max_rate = domain_pump.get_max_rate(
            inlet_stream=self.inlet_stream_condition, target_pressure=Pressure(value=50, unit=Unit.BARA)
        )

        assert max_rate == 36000

        domain_pump.evaluate(streams=[self.inlet_stream_condition, self.outlet_stream_condition])

    def test_compare_v1_and_v2_pumps(self):
        """
        To make sure that v2 is correct (assuming that v1 is correct), at least compare the 2 versions. This should also
        be done when running..if possible, in parallel, for a period of time to make sure that v2 consistently returns the same as
        v1. If there are differences, it may be that v2 is correct, but it should nevertheless be verified

        Returns:

        """
        # TODO: Fix
        from libecalc.core.models.pump import PumpSingleSpeed as CorePumpSingleSpeed

        pump_model: dto.PumpModel = self.pump_model_references.models.get("pump_single_speed")

        from libecalc.core.models.chart.single_speed_chart import (
            SingleSpeedChart as CoreSingleSpeedChart,
        )

        # TODO: Change to pump v1 yaml for better testing
        chart = CoreSingleSpeedChart.create(
            speed_rpm=pump_model.chart.speed_rpm,
            rate_actual_m3_hour=pump_model.chart.rate_actual_m3_hour,
            polytropic_head_joule_per_kg=pump_model.chart.polytropic_head_joule_per_kg,
            efficiency_fraction=pump_model.chart.efficiency_fraction,
        )
        pump_v1 = CorePumpSingleSpeed(pump_chart=chart)

        pump_v2 = self.yaml_pump.to_domain_model(
            timestep=datetime(year=2020, month=1, day=1), references=self.pump_model_references
        )

        pump_v2_result = pump_v2.evaluate(streams=[self.inlet_stream_condition, self.outlet_stream_condition])
        print(f"result: {pump_v2_result}")

        pump_v1_result = pump_v1.evaluate_rate_ps_pd_density(
            fluid_density=np.asarray([self.inlet_stream_condition.density.value]),
            rate=np.asarray([self.inlet_stream_condition.rate.value]),
            suction_pressures=np.asarray([self.inlet_stream_condition.pressure.value]),
            discharge_pressures=np.asarray([self.outlet_stream_condition.pressure.value]),
        )

        assert pump_v1_result.energy_usage[0] == pump_v2_result.component_result.energy_usage.values[0]
