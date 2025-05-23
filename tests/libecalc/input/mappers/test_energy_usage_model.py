import io
from datetime import datetime
from typing import Union

import pytest
from pydantic import TypeAdapter, ValidationError

import libecalc.common.energy_usage_type
import libecalc.common.utils.rates
from libecalc.domain.process import dto
from libecalc.domain.process.dto.consumer_system import (
    PumpSystemConsumerFunction,
    PumpSystemPump,
    PumpSystemOperationalSetting,
)
from libecalc.domain.process.pump.pump import PumpModelDTO
from libecalc.common.serializable_chart import SingleSpeedChartDTO
from libecalc.common.time_utils import Period
from libecalc.common.units import Unit
from libecalc.dto.utils.validators import convert_expressions
from libecalc.expression import Expression
from libecalc.presentation.yaml.mappers.consumer_function_mapper import (
    ConsumerFunctionMapper,
)
from libecalc.presentation.yaml.yaml_entities import References, ResourceStream
from libecalc.presentation.yaml.yaml_models.pyyaml_yaml_model import PyYamlYamlModel
from libecalc.presentation.yaml.yaml_types.components.legacy.energy_usage_model import (
    YamlElectricityEnergyUsageModel,
    YamlFuelEnergyUsageModel,
)
from libecalc.presentation.yaml.yaml_types.yaml_temporal_model import YamlTemporalModel

SINGLE_SPEED_PUMP_CHART = PumpModelDTO(
    chart=SingleSpeedChartDTO(
        rate_actual_m3_hour=[20, 200, 60, 10000],
        polytropic_head_joule_per_kg=[
            Unit.POLYTROPIC_HEAD_METER_LIQUID_COLUMN.to(Unit.POLYTROPIC_HEAD_JOULE_PER_KG)(x)
            for x in [25.0, 250.0, 65.0, 10000.0]
        ],
        efficiency_fraction=[0.30, 0.300, 0.70, 1],
        speed_rpm=1,
    ),
    energy_usage_adjustment_constant=0.0,
    energy_usage_adjustment_factor=1.0,
    head_margin=0.0,
)
pump_system = (
    """
    TYPE: PUMP_SYSTEM
    CONDITION: 'SIM1;WATER_PROD >0'
    PUMPS:
    - NAME: pump1
      CHART: waterinj
    - NAME: pump2
      CHART: waterinj
    - NAME: pump3
      CHART: waterinj
    - NAME: pump4
      CHART: waterinj
    FLUID_DENSITY: 1026
    TOTAL_SYSTEM_RATE: SIM1;WATER_INJ
    OPERATIONAL_SETTINGS:
    - RATE_FRACTIONS: [1, 0, 0, 0]
      # RATES: ['SIM1;WATER_INJ'] # Optional notation? Support both, but only one may be specified per setting
      SUCTION_PRESSURES: [3, 3, 3, 3]
      DISCHARGE_PRESSURES: [200, 200, 200, 200]
      CROSSOVER: [2, 0, 0, 0]
    - RATE_FRACTIONS: [0.5, 0.5, 0, 0]
      SUCTION_PRESSURE: 3
      DISCHARGE_PRESSURE: 200
    - RATE_FRACTIONS: [0.33, 0.33, 0.34, 0]
      SUCTION_PRESSURE: 3
      DISCHARGE_PRESSURE: 200
    - RATE_FRACTIONS:  [0.25, 0.25, 0.25, 0.25]
      SUCTION_PRESSURE: 3
      DISCHARGE_PRESSURE: 200
    """,
    PumpSystemConsumerFunction(
        condition=Expression.setup_from_expression(value="SIM1;WATER_PROD >0"),
        pumps=[
            PumpSystemPump(
                name="pump1",
                pump_model=SINGLE_SPEED_PUMP_CHART,
            ),
            PumpSystemPump(
                name="pump2",
                pump_model=SINGLE_SPEED_PUMP_CHART,
            ),
            PumpSystemPump(
                name="pump3",
                pump_model=SINGLE_SPEED_PUMP_CHART,
            ),
            PumpSystemPump(
                name="pump4",
                pump_model=SINGLE_SPEED_PUMP_CHART,
            ),
        ],
        fluid_density=Expression.setup_from_expression(value="1026"),
        total_system_rate=Expression.setup_from_expression(value="SIM1;WATER_INJ"),
        operational_settings=[
            PumpSystemOperationalSetting(
                rate_fractions=convert_expressions([1, 0, 0, 0]),
                suction_pressures=convert_expressions([3, 3, 3, 3]),
                discharge_pressures=convert_expressions([200, 200, 200, 200]),
                crossover=[2, 0, 0, 0],
            ),
            PumpSystemOperationalSetting(
                rate_fractions=convert_expressions([0.5, 0.5, 0, 0]),
                suction_pressure=Expression.setup_from_expression(value=3),
                discharge_pressure=Expression.setup_from_expression(value=200),
            ),
            PumpSystemOperationalSetting(
                rate_fractions=convert_expressions([0.33, 0.33, 0.34, 0]),
                suction_pressure=Expression.setup_from_expression(value=3),
                discharge_pressure=Expression.setup_from_expression(value=200),
            ),
            PumpSystemOperationalSetting(
                rate_fractions=convert_expressions([0.25, 0.25, 0.25, 0.25]),
                suction_pressure=Expression.setup_from_expression(value=3),
                discharge_pressure=Expression.setup_from_expression(value=200),
            ),
        ],
    ),
    References(
        models={
            "waterinj": PumpModelDTO(
                chart=SingleSpeedChartDTO(
                    rate_actual_m3_hour=[20, 200, 60, 10000],
                    polytropic_head_joule_per_kg=[
                        Unit.POLYTROPIC_HEAD_METER_LIQUID_COLUMN.to(Unit.POLYTROPIC_HEAD_JOULE_PER_KG)(x)
                        for x in [25, 250, 65, 10000]
                    ],
                    efficiency_fraction=[0.30, 0.300, 0.70, 1],
                    speed_rpm=1,
                ),
                energy_usage_adjustment_constant=0.0,
                energy_usage_adjustment_factor=1.0,
                head_margin=0.0,
            )
        },
    ),
)

direct = (
    """
TYPE: DIRECT
LOAD: 4.1 # MW
CONDITION: SIM2;GAS_LIFT > 0
    """,
    dto.DirectConsumerFunction(
        load=Expression.setup_from_expression(value="4.1"),
        condition=Expression.setup_from_expression(value="SIM2;GAS_LIFT > 0"),
        energy_usage_type=libecalc.common.energy_usage_type.EnergyUsageType.POWER,
        consumption_rate_type=libecalc.common.utils.rates.RateType.STREAM_DAY,
    ),
    None,
)


class TestEnergyUsageModelMapper:
    @pytest.mark.parametrize("yaml_text,expected_model_dto,references", [pump_system, direct])
    def test_energy_usage_model_valid(self, yaml_text, expected_model_dto, references):
        read_yaml = PyYamlYamlModel.read_yaml(ResourceStream(name="main.yaml", stream=io.StringIO(yaml_text)))
        model_dto = ConsumerFunctionMapper(
            references, target_period=Period(start=datetime.min, end=datetime.max.replace(microsecond=0))
        ).from_yaml_to_dto(
            TypeAdapter(Union[YamlFuelEnergyUsageModel, YamlElectricityEnergyUsageModel]).validate_python(read_yaml)
        )
        model_dto_without_default_date = next(iter(model_dto.values()))
        assert model_dto_without_default_date == expected_model_dto

    def test_condition_and_conditions_error(self):
        read_yaml = PyYamlYamlModel.read_yaml(
            ResourceStream(
                name="direct.yaml",
                stream=io.StringIO(
                    """
TYPE: DIRECT
LOAD: 4.1 # MW
CONDITION: SIM2;GAS_LIFT > 0
CONDITIONS:
  - 5
  - 6
    """
                ),
            )
        )
        with pytest.raises(ValidationError) as exc_info:
            TypeAdapter(
                Union[
                    YamlTemporalModel[YamlFuelEnergyUsageModel],
                    YamlTemporalModel[YamlElectricityEnergyUsageModel],
                ],
            ).validate_python(read_yaml)

        assert "Either CONDITION or CONDITIONS should be specified, not both." in str(exc_info.value)
