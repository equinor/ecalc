from datetime import datetime
from io import StringIO
from typing import Any, Dict

import pytest
from libecalc import dto
from libecalc.common.time_utils import Period
from libecalc.presentation.yaml.mappers.component_mapper import EcalcModelMapper
from libecalc.presentation.yaml.mappers.create_references import create_references
from libecalc.presentation.yaml.mappers.model import ModelMapper
from libecalc.presentation.yaml.yaml_entities import Resource, ResourceStream
from libecalc.presentation.yaml.yaml_keywords import EcalcYamlKeywords
from libecalc.presentation.yaml.yaml_models.pyyaml_yaml_model import PyYamlYamlModel


class TestModelMapper:
    @staticmethod
    def test_predefined_variable_speed_compressor_chart_from_yaml_to_dto():
        resources = {
            "einput/predefined_compressor_chart_curves.csv": Resource(
                headers=["SPEED", "RATE", "HEAD", "EFFICIENCY"],
                data=[
                    [
                        7689,
                        7689,
                        7689,
                        7689,
                        8787,
                        8787,
                        8787,
                        8787,
                        8787,
                        9886,
                        9886,
                        9886,
                        9886,
                        9886,
                        10435,
                        10435,
                        10435,
                        10435,
                        10435,
                        10984,
                        10984,
                        10984,
                        10984,
                        10984,
                        11533,
                        11533,
                        11533,
                        11533,
                        11533,
                        11533,
                        10767,
                        10767,
                        10767,
                        10767,
                        10767,
                        10767,
                    ],
                    [
                        2900.0666,
                        3503.8068,
                        4002.5554,
                        4595.0148,
                        3305.5723,
                        4000.1546,
                        4499.2342,
                        4996.8728,
                        5241.9892,
                        3708.8713,
                        4502.2531,
                        4993.5959,
                        5507.8114,
                        5924.3308,
                        3928.0389,
                        4507.4654,
                        5002.1249,
                        5498.9912,
                        6248.5937,
                        4138.6974,
                        5002.4758,
                        5494.3704,
                        6008.6962,
                        6560.148,
                        4327.9175,
                        4998.517,
                        5505.8851,
                        6027.6167,
                        6506.9064,
                        6908.2832,
                        4052.9057,
                        4500.6637,
                        4999.41,
                        5492.822,
                        6000.6263,
                        6439.4876,
                    ],
                    [
                        8412.9156,
                        7996.2541,
                        7363.8161,
                        6127.1702,
                        10950.9557,
                        10393.3867,
                        9707.491,
                        8593.8586,
                        7974.6002,
                        13845.3808,
                        13182.6922,
                        12425.3699,
                        11276.3984,
                        10054.3539,
                        15435.484,
                        14982.7351,
                        14350.2222,
                        13361.3245,
                        11183.0276,
                        17078.8952,
                        16274.9249,
                        15428.5063,
                        14261.7156,
                        12382.7538,
                        18882.3055,
                        18235.1912,
                        17531.6259,
                        16489.7195,
                        15037.1474,
                        13618.7919,
                        16447,
                        16081,
                        15546,
                        14640,
                        13454,
                        11973,
                    ],
                    [
                        0.723,
                        0.7469,
                        0.7449,
                        0.7015,
                        0.7241,
                        0.7449,
                        0.7464,
                        0.722,
                        0.7007,
                        0.723,
                        0.7473,
                        0.748,
                        0.7306,
                        0.704,
                        0.7232,
                        0.7437,
                        0.7453,
                        0.7414,
                        0.701,
                        0.7226,
                        0.7462,
                        0.7468,
                        0.7349,
                        0.7023,
                        0.7254,
                        0.7444,
                        0.745,
                        0.7466,
                        0.7266,
                        0.7019,
                        0.724,
                        0.738,
                        0.7479,
                        0.74766,
                        0.7298,
                        0.7014,
                    ],
                ],
            ),
        }

        model_mapper = ModelMapper(resources=resources)
        variable_speed_compressor_chart_curves_spec_in_csv = model_mapper.from_yaml_to_dto(
            model_config={
                "NAME": "predefined_compressor_chart_curves_from_file",
                "TYPE": "COMPRESSOR_CHART",
                "CHART_TYPE": "VARIABLE_SPEED",
                "UNITS": {"RATE": "AM3_PER_HOUR", "HEAD": "M", "EFFICIENCY": "FRACTION"},
                "CURVES": {"FILE": "einput/predefined_compressor_chart_curves.csv"},
            },
            input_models={},
        )
        variable_speed_compressor_chart_curves_spec_in_yaml = model_mapper.from_yaml_to_dto(
            model_config={
                "NAME": "predefined_compressor_chart",
                "TYPE": "COMPRESSOR_CHART",
                "CHART_TYPE": "VARIABLE_SPEED",
                "UNITS": {"RATE": "AM3_PER_HOUR", "HEAD": "M", "EFFICIENCY": "FRACTION"},
                "CURVES": [
                    {
                        "SPEED": 7689,
                        "RATE": [2900.0666, 3503.8068, 4002.5554, 4595.0148],
                        "HEAD": [8412.9156, 7996.2541, 7363.8161, 6127.1702],
                        "EFFICIENCY": [0.723, 0.7469, 0.7449, 0.7015],
                    },
                    {
                        "SPEED": 8787,
                        "RATE": [3305.5723, 4000.1546, 4499.2342, 4996.8728, 5241.9892],
                        "HEAD": [10950.9557, 10393.3867, 9707.491, 8593.8586, 7974.6002],
                        "EFFICIENCY": [0.7241, 0.7449, 0.7464, 0.722, 0.7007],
                    },
                    {
                        "SPEED": 9886,
                        "RATE": [3708.8713, 4502.2531, 4993.5959, 5507.8114, 5924.3308],
                        "HEAD": [13845.3808, 13182.6922, 12425.3699, 11276.3984, 10054.3539],
                        "EFFICIENCY": [0.723, 0.7473, 0.748, 0.7306, 0.704],
                    },
                    {
                        "SPEED": 10435,
                        "RATE": [3928.0389, 4507.4654, 5002.1249, 5498.9912, 6248.5937],
                        "HEAD": [15435.484, 14982.7351, 14350.2222, 13361.3245, 11183.0276],
                        "EFFICIENCY": [0.7232, 0.7437, 0.7453, 0.7414, 0.701],
                    },
                    {
                        "SPEED": 10984,
                        "RATE": [4138.6974, 5002.4758, 5494.3704, 6008.6962, 6560.148],
                        "HEAD": [17078.8952, 16274.9249, 15428.5063, 14261.7156, 12382.7538],
                        "EFFICIENCY": [0.7226, 0.7462, 0.7468, 0.7349, 0.7023],
                    },
                    {
                        "SPEED": 11533,
                        "RATE": [4327.9175, 4998.517, 5505.8851, 6027.6167, 6506.9064, 6908.2832],
                        "HEAD": [18882.3055, 18235.1912, 17531.6259, 16489.7195, 15037.1474, 13618.7919],
                        "EFFICIENCY": [0.7254, 0.7444, 0.745, 0.7466, 0.7266, 0.7019],
                    },
                    {
                        "SPEED": 10767,
                        "RATE": [4052.9057, 4500.6637, 4999.41, 5492.822, 6000.6263, 6439.4876],
                        "HEAD": [16447, 16081, 15546, 14640, 13454, 11973],
                        "EFFICIENCY": [0.724, 0.738, 0.7479, 0.74766, 0.7298, 0.7014],
                    },
                ],
            },
            input_models={},
        )
        assert variable_speed_compressor_chart_curves_spec_in_csv == variable_speed_compressor_chart_curves_spec_in_yaml


@pytest.fixture
def dated_model_source() -> str:
    return """
TIME_SERIES: []

FACILITY_INPUTS: []

FUEL_TYPES:
  - NAME: fuel_gas
    PRICE: 1.5  # NOK/Sm3
    CATEGORY: FUEL-GAS
    EMISSIONS:
      - NAME: co2
        FACTOR: "2.20" #kg/Sm3
        TAX: 1.51 # NOK/Sm3

INSTALLATIONS:
  - NAME: dated
    HCEXPORT:
      2020-01-01: 5
      2025-01-01: 10
    FUEL: fuel_gas
    FUELCONSUMERS:
      - NAME: late_start_consumer
        CATEGORY: FIXED-PRODUCTION-LOAD
        ENERGY_USAGE_MODEL:
          2020-01-01:
            TYPE: DIRECT
            FUELRATE: 1
          2022-01-01:
            TYPE: DIRECT
            FUELRATE: 2
          2030-01-01:
            TYPE: DIRECT
            FUELRATE: 0
"""


@pytest.fixture
def dated_model_data(dated_model_source: str) -> Dict[str, Any]:
    return PyYamlYamlModel.read_yaml(
        main_yaml=ResourceStream(stream=StringIO(dated_model_source), name="model.yaml"),
        enable_include=False,
    )


def parse_model(model_data, start: datetime, end: datetime) -> dto.Asset:
    period = Period(
        start=start,
        end=end,
    )
    model_data[EcalcYamlKeywords.start] = period.start
    model_data[EcalcYamlKeywords.end] = period.end

    configuration = PyYamlYamlModel(internal_datamodel=model_data, instantiated_through_read=True)
    references = create_references(configuration, resources={})
    model_mapper = EcalcModelMapper(references=references, target_period=period)
    return model_mapper.from_yaml_to_dto(configuration, name="test")


class TestDatedModelFilter:
    def test_include_all(self, dated_model_data):
        model = parse_model(
            model_data=dated_model_data,
            start=datetime(2020, 1, 1),
            end=datetime(2040, 1, 1),
        )

        assert list(model.installations[0].fuel_consumers[0].energy_usage_model.keys()) == [
            datetime(2020, 1, 1),
            datetime(2022, 1, 1),
            datetime(2030, 1, 1),
        ]
        assert list(model.installations[0].fuel_consumers[0].fuel.keys()) == [
            datetime(2020, 1, 1),
        ]
        assert list(model.installations[0].hydrocarbon_export.keys()) == [
            datetime(2020, 1, 1),
            datetime(2025, 1, 1),
        ]

    def test_include_start(self, dated_model_data):
        model = parse_model(
            model_data=dated_model_data,
            start=datetime(2020, 1, 1),
            end=datetime(2025, 1, 1),
        )

        assert list(model.installations[0].fuel_consumers[0].energy_usage_model.keys()) == [
            datetime(2020, 1, 1),
            datetime(2022, 1, 1),
        ]
        assert list(model.installations[0].fuel_consumers[0].fuel.keys()) == [datetime(2020, 1, 1)]
        assert list(model.installations[0].hydrocarbon_export.keys()) == [
            datetime(2020, 1, 1),
        ]

    def test_include_end(self, dated_model_data):
        model = parse_model(
            model_data=dated_model_data,
            start=datetime(2026, 1, 1),
            end=datetime(2040, 1, 1),
        )

        assert list(model.installations[0].fuel_consumers[0].energy_usage_model.keys()) == [
            datetime(2026, 1, 1),
            datetime(2030, 1, 1),
        ]
        assert list(model.installations[0].fuel_consumers[0].fuel.keys()) == [
            datetime(2026, 1, 1),
        ]
        assert list(model.installations[0].hydrocarbon_export.keys()) == [
            datetime(2026, 1, 1),
        ]

    def test_include_middle(self, dated_model_data):
        model = parse_model(
            model_data=dated_model_data,
            start=datetime(2023, 1, 1),
            end=datetime(2029, 1, 1),
        )

        assert list(model.installations[0].fuel_consumers[0].energy_usage_model.keys()) == [
            datetime(2023, 1, 1),
        ]
        assert list(model.installations[0].fuel_consumers[0].fuel.keys()) == [
            datetime(2023, 1, 1),
        ]
        assert list(model.installations[0].hydrocarbon_export.keys()) == [
            datetime(2023, 1, 1),
            datetime(2025, 1, 1),
        ]
