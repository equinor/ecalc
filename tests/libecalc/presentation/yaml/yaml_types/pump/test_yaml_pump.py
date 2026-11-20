from io import StringIO

import pytest
import yaml
from pydantic import ValidationError

from libecalc.presentation.yaml.yaml_entities import ResourceStream
from libecalc.presentation.yaml.yaml_models.pyyaml_yaml_model import PyYamlYamlModel
from libecalc.presentation.yaml.yaml_types.components.yaml_asset import YamlAsset
from libecalc.presentation.yaml.yaml_types.process.yaml_process_units import YamlPressureDropperDefinition
from libecalc.presentation.yaml.yaml_types.pump.yaml_liquid_stream import YamlLiquidInletStream
from libecalc.presentation.yaml.yaml_types.pump.yaml_pump_model import YamlPumpModel
from libecalc.presentation.yaml.yaml_types.pump.yaml_pump_pipeline import YamlPumpPipeline, YamlPumpProcessUnit
from libecalc.presentation.yaml.yaml_types.pump.yaml_pump_simulation import (
    YamlPumpCommonStreamDistribution,
    YamlPumpConstraint,
    YamlPumpIndividualStreamDistribution,
    YamlPumpPressureControl,
    YamlPumpSimulation,
)
from libecalc.presentation.yaml.yaml_validation_context import YamlModelValidationContextNames

PUMP_MODEL = """
TYPE: PUMP_CHART
CHART:
  CURVES:
    - SPEED: 1
      RATE: [277, 524, 666, 832, 927]
      HEAD: [1062, 1004, 944, 847, 776]
      EFFICIENCY: [47.6, 64.3, 68.7, 70.5, 69.1]
  UNITS: {RATE: AM3_PER_HOUR, HEAD: M, EFFICIENCY: PERCENTAGE}
"""

MODEL = """
END: 2030-01-01
TIMELINE:
  EVENTS:
    event:
      TYPE: OTHER
      FROM: 2021-07-01
PUMPS:
  - NAME: pump_a
  - NAME: pump_b
  - NAME: pump_c
    ALIAS: Pump C
PUMP_PIPELINES:
  - NAME: line_a
    PROCESS_UNITS:
      - TYPE: PUMP
        PUMP: pump_a
        MODEL: pump_model_a
  - NAME: line_b
    PROCESS_UNITS:
      - TYPE: PUMP
        PUMP: pump_b
        MODEL: pump_model_a
  - NAME: line_c
    PROCESS_UNITS:
      - TYPE: PRESSURE_DROPPER
        PRESSURE_DROP: 4
      - TYPE: PUMP
        PUMP: pump_c
        MODEL: pump_model_b
PUMP_SIMULATIONS:
  - NAME: pump_simulation
    TARGETS: [line_a, line_b, line_c]
    STREAM_DISTRIBUTION:
      METHOD: COMMON_STREAM
      INLET_STREAM:
        NAME: inlet
        PRESSURE: 10
        DENSITY: 1022
        RATE:
          VALUE: SIM;RATE_A {+} SIM;RATE_B
          UNIT: M3_PER_DAY
          TYPE: STREAM_DAY
      SETTINGS:
        - RATE_FRACTIONS: [0, 1, 0]
        - RATE_FRACTIONS: [0.5, 0, 0.5]
    CONSTRAINTS:
      line_a:
        - OUTLET_PRESSURE: 240
      line_b:
        - OUTLET_PRESSURE: 205
      line_c:
        - OUTLET_PRESSURE: 190
"""


def _read(model_data: dict) -> PyYamlYamlModel:
    return PyYamlYamlModel.read(
        ResourceStream(name="pump_model", stream=StringIO(PyYamlYamlModel.dump_yaml(yaml_dict=model_data)))
    )


@pytest.fixture
def model_data() -> dict:
    model_data = yaml.safe_load(MODEL)
    pump_model = yaml.safe_load(PUMP_MODEL)
    model_data["DEFINITIONS"] = {
        "PUMP_MODELS": {"pump_model_a": pump_model | {"MINIMUM_FLOW_RATE": 300}, "pump_model_b": pump_model}
    }
    return model_data


def test_nextgen_asset_with_pump_sections(model_data):
    asset = YamlAsset.model_validate(model_data, context={YamlModelValidationContextNames.nextgen: True})

    assert set(asset.definitions.pump_models) == {"pump_model_a", "pump_model_b"}
    assert asset.definitions.pump_models["pump_model_a"].minimum_flow_rate == 300
    assert asset.definitions.pump_models["pump_model_b"].minimum_flow_rate is None
    assert [pump.name for pump in asset.pumps] == ["pump_a", "pump_b", "pump_c"]
    assert asset.pumps[2].alias == "Pump C"
    assert [pipeline.name for pipeline in asset.pump_pipelines] == ["line_a", "line_b", "line_c"]
    pressure_dropper, pump_unit = asset.pump_pipelines[2].process_units
    assert isinstance(pressure_dropper, YamlPressureDropperDefinition)
    assert isinstance(pump_unit, YamlPumpProcessUnit)
    assert pump_unit.pump == "pump_c"
    assert pump_unit.model == "pump_model_b"

    [simulation] = asset.pump_simulations
    assert simulation.targets == ["line_a", "line_b", "line_c"]
    assert isinstance(simulation.stream_distribution, YamlPumpCommonStreamDistribution)
    assert simulation.stream_distribution.inlet_stream.rate.value == "SIM;RATE_A {+} SIM;RATE_B"
    assert [setting.rate_fractions for setting in simulation.stream_distribution.settings] == [
        [0, 1, 0],
        [0.5, 0, 0.5],
    ]
    assert {target: [c.outlet_pressure for c in cs] for target, cs in simulation.constraints.items()} == {
        "line_a": [240],
        "line_b": [205],
        "line_c": [190],
    }


def test_pump_sections_are_not_available_in_legacy_model(model_data):
    with pytest.raises(ValidationError, match="not available in a legacy model: .*PUMPS"):
        YamlAsset.model_validate(model_data, context={YamlModelValidationContextNames.nextgen: False})


def test_pyyaml_model_reads_pump_sections(model_data):
    yaml_model = _read(model_data)

    assert set(yaml_model.definitions.pump_models) == {"pump_model_a", "pump_model_b"}
    assert [pump.name for pump in yaml_model.pumps] == ["pump_a", "pump_b", "pump_c"]
    assert [pipeline.name for pipeline in yaml_model.pump_pipelines] == ["line_a", "line_b", "line_c"]
    assert [simulation.name for simulation in yaml_model.pump_simulations] == ["pump_simulation"]


def test_pyyaml_model_skips_invalid_pump_items(model_data):
    model_data["PUMP_PIPELINES"].append({"NAME": "broken"})

    yaml_model = _read(model_data)

    assert [pipeline.name for pipeline in yaml_model.pump_pipelines] == ["line_a", "line_b", "line_c"]


def test_pump_process_unit_accepts_inline_model():
    unit = YamlPumpProcessUnit.model_validate({"TYPE": "PUMP", "PUMP": "pump_a", "MODEL": yaml.safe_load(PUMP_MODEL)})

    assert isinstance(unit.model, YamlPumpModel)


def test_pump_pipeline_allows_same_pump_twice_in_yaml():
    pump_unit = {"TYPE": "PUMP", "PUMP": "pump_a", "MODEL": "pump_model_a"}

    pipeline = YamlPumpPipeline.model_validate({"NAME": "line", "PROCESS_UNITS": [pump_unit, pump_unit]})

    assert len(pipeline.process_units) == 2


def test_pump_pipeline_rejects_unknown_process_unit_type():
    with pytest.raises(ValidationError, match="does not match any of the expected tags"):
        YamlPumpPipeline.model_validate({"NAME": "line", "PROCESS_UNITS": [{"TYPE": "COMPRESSOR"}]})


def test_pump_model_has_no_head_margin():
    with pytest.raises(ValidationError, match="HEAD_MARGIN"):
        YamlPumpModel.model_validate(yaml.safe_load(PUMP_MODEL) | {"HEAD_MARGIN": 0.1})


@pytest.mark.parametrize(
    "rate, message",
    [
        ({"VALUE": 100, "UNIT": "SM3_PER_DAY"}, "UNIT"),
        ({"VALUE": 100, "UNIT": "M3_PER_DAY", "TYPE": "CALENDAR_DAY"}, "TYPE"),
        ({"VALUE": 100, "UNIT": "M3_PER_DAY", "CONDITION": "a > 0"}, "CONDITION"),
    ],
)
def test_liquid_inlet_stream_rejects_invalid_rate(rate, message):
    with pytest.raises(ValidationError, match=message):
        YamlLiquidInletStream.model_validate({"NAME": "header", "PRESSURE": 10, "DENSITY": 1022, "RATE": rate})


def test_pump_simulation_individual_streams():
    stream = {"NAME": "a", "PRESSURE": 10, "DENSITY": 1022, "RATE": {"VALUE": 100, "UNIT": "M3_PER_DAY"}}

    simulation = YamlPumpSimulation.model_validate(
        {
            "NAME": "sim",
            "TARGETS": ["line"],
            "STREAM_DISTRIBUTION": {"METHOD": "INDIVIDUAL_STREAMS", "INLET_STREAMS": [stream]},
            "CONSTRAINTS": {"line": [{"OUTLET_PRESSURE": 200}]},
        }
    )

    assert isinstance(simulation.stream_distribution, YamlPumpIndividualStreamDistribution)
    assert simulation.stream_distribution.inlet_streams[0].name == "a"


def test_pump_simulation_rejects_inlet_stream_reference():
    with pytest.raises(ValidationError, match="INLET_STREAM"):
        YamlPumpSimulation.model_validate(
            {
                "NAME": "sim",
                "TARGETS": ["line"],
                "STREAM_DISTRIBUTION": {
                    "METHOD": "COMMON_STREAM",
                    "INLET_STREAM": "header",
                    "SETTINGS": [{"RATE_FRACTIONS": [1]}],
                },
                "CONSTRAINTS": {"line": [{"OUTLET_PRESSURE": 200}]},
            }
        )


def test_pump_constraint_process_unit_is_optional():
    assert YamlPumpConstraint.model_validate({"OUTLET_PRESSURE": 200}).process_unit is None
    assert (
        YamlPumpConstraint.model_validate({"PROCESS_UNIT": "pump_a", "OUTLET_PRESSURE": 200}).process_unit == "pump_a"
    )


@pytest.mark.parametrize(
    "constraint, expected",
    [
        ({"OUTLET_PRESSURE": 200}, YamlPumpPressureControl.NONE),
        ({"OUTLET_PRESSURE": 200, "PRESSURE_CONTROL": "NONE"}, YamlPumpPressureControl.NONE),
        ({"OUTLET_PRESSURE": 200, "PRESSURE_CONTROL": "DOWNSTREAM_CHOKE"}, YamlPumpPressureControl.DOWNSTREAM_CHOKE),
    ],
)
def test_pump_constraint_pressure_control(constraint, expected):
    assert YamlPumpConstraint.model_validate(constraint).pressure_control == expected


@pytest.mark.parametrize("pressure_control", ["UPSTREAM_CHOKE", "COMMON_ASV"])
def test_pump_constraint_rejects_other_pressure_control(pressure_control):
    with pytest.raises(ValidationError, match="PRESSURE_CONTROL"):
        YamlPumpConstraint.model_validate({"OUTLET_PRESSURE": 200, "PRESSURE_CONTROL": pressure_control})
