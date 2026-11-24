from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from io import StringIO

import pytest
import yaml

from libecalc.ecalc_model.process.pump.pump_pipeline import PumpPipeline
from libecalc.ecalc_model.process.pump.pump_simulation_evaluation import (
    PumpSimulationPeriodResult,
    evaluate_pump_simulation,
)
from libecalc.presentation.yaml.yaml_entities import MemoryResource, ResourceStream
from libecalc.presentation.yaml.yaml_types.pump.yaml_pump_model import YamlPumpModel
from libecalc.process.pump.pump import PumpFailureStatus
from libecalc.testing.pump_builders import YamlPumpChartBuilder, YamlPumpModelBuilder

# The pump models of every model below. With the density of 1000 kg/m3, the single-speed chart has a head of
# 90, 85, 80, 70 and 60 bar at 200, 400, 600, 800 and 1000 m3/h, at 2000 rpm. The variable-speed chart has that
# curve and one of 175, 170, 160, 150 and 130 bar at 300, 600, 800, 1000 and 1200 m3/h, at 3000 rpm.
SINGLE_SPEED = YamlPumpModelBuilder().with_test_data().validate()
VARIABLE_SPEED = (
    YamlPumpModelBuilder().with_chart(YamlPumpChartBuilder().with_variable_speed_test_data().validate()).validate()
)


def _dump(pump_model: YamlPumpModel) -> dict:
    return pump_model.model_dump(mode="json", exclude_unset=True, by_alias=True)


PUMP_MODELS = {
    "single_speed": _dump(SINGLE_SPEED),
    "single_speed_with_a_minimum_flow_of_300": _dump(SINGLE_SPEED) | {"MINIMUM_FLOW_RATE": 300},
    "variable_speed": _dump(VARIABLE_SPEED),
}
PERIODS_FILE = "periods.csv"


@dataclass(frozen=True)
class PumpSummary:
    speed_rpm: float | None
    failure_status: PumpFailureStatus = PumpFailureStatus.NO_FAILURE
    outlet_pressure_above_requested: bool = False


@dataclass(frozen=True)
class PipelineSummary:
    """The streams on the connections of a pump pipeline, in flow order, and its pumps."""

    rates_m3_per_hour: list[float]
    pressures_bara: list[float]
    pumps: list[PumpSummary]


@dataclass(frozen=True, kw_only=True)
class PeriodSummary:
    selected_setting_index: int
    is_valid: bool
    pipelines: list[PipelineSummary]


def _summarise(period_result: PumpSimulationPeriodResult, pump_pipelines: Sequence[PumpPipeline]) -> PeriodSummary:
    pipelines = []
    for pump_pipeline, pipeline_result in zip(pump_pipelines, period_result.pipeline_results, strict=True):
        streams = [
            pipeline_result.connection_streams[connection.get_id()]
            for connection in pump_pipeline.get_process_unit_connections()
        ]
        pumps = []
        for problem_result in pipeline_result.problem_results:
            solution = problem_result.solution
            speed_rpm = solution.pump_result.speed_rpm
            pumps.append(
                PumpSummary(
                    speed_rpm=round(speed_rpm, 6) if speed_rpm is not None else None,
                    failure_status=solution.pump_result.failure_status,
                    outlet_pressure_above_requested=solution.outlet_pressure_above_requested,
                )
            )
        pipelines.append(
            PipelineSummary(
                rates_m3_per_hour=[round(stream.volumetric_rate_m3_per_hour, 6) for stream in streams],
                pressures_bara=[round(stream.pressure_bara, 6) for stream in streams],
                pumps=pumps,
            )
        )
    return PeriodSummary(
        selected_setting_index=period_result.selected_setting_index,
        is_valid=period_result.is_valid,
        pipelines=pipelines,
    )


@pytest.fixture
def evaluate_model(yaml_model_factory):
    """Evaluates the pump simulation of a YAML model, which gets ``PUMP_MODELS`` as its pump models.

    ``values_by_period`` holds the columns of the time series file ``PERIODS_FILE``, with one value per year
    from 2020.
    """

    def evaluate(
        model_data: dict, values_by_period: Mapping[str, Sequence[float]] | None = None
    ) -> list[PeriodSummary]:
        resources = {}
        if values_by_period is not None:
            [number_of_periods] = {len(values) for values in values_by_period.values()}
            resources[PERIODS_FILE] = MemoryResource(
                headers=["DATE", *values_by_period],
                data=[[2020 + year for year in range(number_of_periods)], *map(list, values_by_period.values())],
            )
        model = yaml_model_factory(
            configuration=ResourceStream(
                name="pump_model",
                stream=StringIO(yaml.dump(model_data | {"DEFINITIONS": {"PUMP_MODELS": PUMP_MODELS}})),
            ),
            resources=resources,
            nextgen=True,
        )
        pump_pipelines, [pump_simulation] = model.get_pump_simulations()
        result = evaluate_pump_simulation(pump_simulation, pump_pipelines)
        return [_summarise(period_result, pump_pipelines) for period_result in result.period_results]

    return evaluate


RATE_LADDER = """
START: 2020-01-01
END: 2026-01-01
TIME_SERIES:
  - NAME: SIM
    TYPE: DEFAULT
    FILE: periods.csv
PUMPS:
  - NAME: pump_1
  - NAME: pump_2
PUMP_PIPELINES:
  - NAME: line_1
    PROCESS_UNITS:
      - TYPE: PUMP
        PUMP: pump_1
        MODEL: single_speed
  - NAME: line_2
    PROCESS_UNITS:
      - TYPE: PRESSURE_DROPPER
        PRESSURE_DROP: 2
      - TYPE: PUMP
        PUMP: pump_2
        MODEL: single_speed
PUMP_SIMULATIONS:
  - NAME: injection
    TARGETS: [line_1, line_2]
    STREAM_DISTRIBUTION:
      METHOD: COMMON_STREAM
      INLET_STREAM:
        NAME: header
        PRESSURE: 10
        DENSITY: 1000
        RATE:
          VALUE: SIM;RATE_M3_PER_HOUR {*} 24
          UNIT: M3_PER_DAY
      SETTINGS:
        - RATE_FRACTIONS: [1, 0]
        - RATE_FRACTIONS: [0.5, 0.5]
    CONSTRAINTS:
      line_1:
        - OUTLET_PRESSURE: 60
          PRESSURE_CONTROL: DOWNSTREAM_CHOKE
      line_2:
        - OUTLET_PRESSURE: 60
          PRESSURE_CONTROL: DOWNSTREAM_CHOKE
"""


def test_rate_ladder(evaluate_model):
    """Two single-speed pumps in parallel, one period per rate.

    The connections of ``line_1`` are those into the mixer, the pump, the splitter, the choke and the outlet.
    ``line_2`` has one into the pressure dropper before them.
    """
    periods = evaluate_model(
        yaml.safe_load(RATE_LADDER), {"RATE_M3_PER_HOUR": [0.0, 100.0, 600.0, 1000.0, 1600.0, 2400.0]}
    )

    stopped = PumpSummary(speed_rpm=None)
    running = PumpSummary(speed_rpm=2000.0)
    above_the_maximum_rate = PumpSummary(speed_rpm=2000.0, failure_status=PumpFailureStatus.ABOVE_MAXIMUM_PUMP_RATE)
    # A stream with no rate passes the pressure dropper unchanged.
    stopped_line_2 = PipelineSummary([0.0] * 6, [10.0] * 6, [stopped])
    assert periods == [
        PeriodSummary(
            selected_setting_index=0,
            is_valid=True,
            pipelines=[PipelineSummary([0.0] * 5, [10.0] * 5, [stopped]), stopped_line_2],
        ),
        # The pump recirculates up to the chart's minimum rate of 200 m3/h, where the head is 90 bar.
        PeriodSummary(
            selected_setting_index=0,
            is_valid=True,
            pipelines=[
                PipelineSummary([100.0, 200.0, 200.0, 100.0, 100.0], [10.0, 10.0, 100.0, 100.0, 60.0], [running]),
                stopped_line_2,
            ],
        ),
        # The head is 80 bar, and the choke drops 30 bar.
        PeriodSummary(
            selected_setting_index=0,
            is_valid=True,
            pipelines=[PipelineSummary([600.0] * 5, [10.0, 10.0, 90.0, 90.0, 60.0], [running]), stopped_line_2],
        ),
        # The chart's maximum rate, where the head is 60 bar.
        PeriodSummary(
            selected_setting_index=0,
            is_valid=True,
            pipelines=[PipelineSummary([1000.0] * 5, [10.0, 10.0, 70.0, 70.0, 60.0], [running]), stopped_line_2],
        ),
        # One pump is above the chart's maximum rate, so both run at 800 m3/h, where the head is 70 bar.
        PeriodSummary(
            selected_setting_index=1,
            is_valid=True,
            pipelines=[
                PipelineSummary([800.0] * 5, [10.0, 10.0, 80.0, 80.0, 60.0], [running]),
                PipelineSummary([800.0] * 6, [10.0, 8.0, 8.0, 78.0, 78.0, 60.0], [running]),
            ],
        ),
        # No setting is valid, so the last one is kept. The head is that of the chart's maximum rate.
        PeriodSummary(
            selected_setting_index=1,
            is_valid=False,
            pipelines=[
                PipelineSummary([1200.0] * 5, [10.0, 10.0, 70.0, 70.0, 60.0], [above_the_maximum_rate]),
                PipelineSummary([1200.0] * 6, [10.0, 8.0, 8.0, 68.0, 68.0, 60.0], [above_the_maximum_rate]),
            ],
        ),
    ]


HEAD_LADDER = """
START: 2020-01-01
END: 2024-01-01
TIME_SERIES:
  - NAME: SIM
    TYPE: DEFAULT
    FILE: periods.csv
PUMPS:
  - NAME: pump
PUMP_PIPELINES:
  - NAME: line
    PROCESS_UNITS:
      - TYPE: PUMP
        PUMP: pump
        MODEL: variable_speed
PUMP_SIMULATIONS:
  - NAME: injection
    TARGETS: [line]
    STREAM_DISTRIBUTION:
      METHOD: COMMON_STREAM
      INLET_STREAM:
        NAME: header
        PRESSURE: 10
        DENSITY: 1000
        RATE:
          VALUE: 600 {*} 24
          UNIT: M3_PER_DAY
      SETTINGS:
        - RATE_FRACTIONS: [1]
    CONSTRAINTS:
      line:
        - OUTLET_PRESSURE: SIM;OUTLET_PRESSURE
          PRESSURE_CONTROL: NONE
"""


def _one_pump_at_600_m3_per_hour(pressures_bara: list[float], pump: PumpSummary, is_valid: bool) -> PeriodSummary:
    return PeriodSummary(
        selected_setting_index=0,
        is_valid=is_valid,
        pipelines=[PipelineSummary([600.0] * len(pressures_bara), pressures_bara, [pump])],
    )


def test_head_ladder(evaluate_model):
    """A variable-speed pump at 600 m3/h, where its head is 80 to 170 bar, one period per outlet pressure.

    The connections are those into the mixer, the pump, the splitter and the outlet. With a choke there is one
    into the choke before the outlet.
    """
    outlet_pressures = {"OUTLET_PRESSURE": [50.0, 135.0, 180.0, 200.0]}
    without_a_choke = yaml.safe_load(HEAD_LADDER)
    with_a_choke = yaml.safe_load(HEAD_LADDER)
    [constraint] = with_a_choke["PUMP_SIMULATIONS"][0]["CONSTRAINTS"]["line"]
    constraint["PRESSURE_CONTROL"] = "DOWNSTREAM_CHOKE"

    above_the_maximum_head = PumpSummary(speed_rpm=3000.0, failure_status=PumpFailureStatus.ABOVE_MAXIMUM_HEAD_AT_RATE)
    assert evaluate_model(without_a_choke, outlet_pressures) == [
        # The pump runs at the minimum speed, and nothing drops the 40 bar down to the requested outlet pressure.
        _one_pump_at_600_m3_per_hour(
            [10.0, 10.0, 90.0, 90.0], PumpSummary(speed_rpm=2000.0, outlet_pressure_above_requested=True), False
        ),
        _one_pump_at_600_m3_per_hour([10.0, 10.0, 135.0, 135.0], PumpSummary(speed_rpm=2500.0), True),
        _one_pump_at_600_m3_per_hour([10.0, 10.0, 180.0, 180.0], PumpSummary(speed_rpm=3000.0), True),
        _one_pump_at_600_m3_per_hour([10.0, 10.0, 180.0, 180.0], above_the_maximum_head, False),
    ]
    # With a choke only the first period differs: the choke drops the 40 bar, and the period is valid.
    assert evaluate_model(with_a_choke, outlet_pressures)[0] == _one_pump_at_600_m3_per_hour(
        [10.0, 10.0, 90.0, 90.0, 50.0], PumpSummary(speed_rpm=2000.0), True
    )


SERIES = """
START: 2020-01-01
END: 2022-01-01
TIME_SERIES:
  - NAME: SIM
    TYPE: DEFAULT
    FILE: periods.csv
PUMPS:
  - NAME: booster
  - NAME: main
PUMP_PIPELINES:
  - NAME: line
    PROCESS_UNITS:
      - TYPE: PUMP
        PUMP: booster
        MODEL: variable_speed
      - TYPE: PUMP
        PUMP: main
        MODEL: single_speed
PUMP_SIMULATIONS:
  - NAME: injection
    TARGETS: [line]
    STREAM_DISTRIBUTION:
      METHOD: COMMON_STREAM
      INLET_STREAM:
        NAME: header
        PRESSURE: 10
        DENSITY: 1000
        RATE:
          VALUE: 600 {*} 24
          UNIT: M3_PER_DAY
      SETTINGS:
        - RATE_FRACTIONS: [1]
    CONSTRAINTS:
      line:
        - PROCESS_UNIT: booster
          OUTLET_PRESSURE: SIM;BOOSTER_OUTLET_PRESSURE
          PRESSURE_CONTROL: NONE
        - PROCESS_UNIT: main
          OUTLET_PRESSURE: 150
          PRESSURE_CONTROL: DOWNSTREAM_CHOKE
"""


def test_booster_without_a_choke_feeds_a_main_pump_with_a_choke(evaluate_model):
    """A variable-speed booster and a single-speed main pump at 600 m3/h, where the main pump's head is 80 bar.

    The connections are those into the booster's mixer, pump and splitter, and into the main pump's mixer, pump,
    splitter and choke, and the outlet.
    """
    periods = evaluate_model(yaml.safe_load(SERIES), {"BOOSTER_OUTLET_PRESSURE": [135.0, 50.0]})

    main = PumpSummary(speed_rpm=2000.0)
    assert periods == [
        PeriodSummary(
            selected_setting_index=0,
            is_valid=True,
            pipelines=[
                PipelineSummary(
                    [600.0] * 8,
                    [10.0, 10.0, 135.0, 135.0, 135.0, 215.0, 215.0, 150.0],
                    [PumpSummary(speed_rpm=2500.0), main],
                )
            ],
        ),
        # The booster runs at the minimum speed, where its head is 80 bar, and the main pump gets its discharge
        # pressure of 90 bara. Only the booster's pump problem is not valid.
        PeriodSummary(
            selected_setting_index=0,
            is_valid=False,
            pipelines=[
                PipelineSummary(
                    [600.0] * 8,
                    [10.0, 10.0, 90.0, 90.0, 90.0, 170.0, 170.0, 150.0],
                    [PumpSummary(speed_rpm=2000.0, outlet_pressure_above_requested=True), main],
                )
            ],
        ),
    ]


INDIVIDUAL_STREAMS = """
START: 2020-01-01
END: 2022-01-01
TIME_SERIES:
  - NAME: SIM
    TYPE: DEFAULT
    FILE: periods.csv
PUMPS:
  - NAME: pump_1
  - NAME: pump_2
PUMP_PIPELINES:
  - NAME: line_1
    PROCESS_UNITS:
      - TYPE: PUMP
        PUMP: pump_1
        MODEL: single_speed_with_a_minimum_flow_of_300
  - NAME: line_2
    PROCESS_UNITS:
      - TYPE: PUMP
        PUMP: pump_2
        MODEL: variable_speed
PUMP_SIMULATIONS:
  - NAME: injection
    TARGETS: [line_1, line_2]
    STREAM_DISTRIBUTION:
      METHOD: INDIVIDUAL_STREAMS
      INLET_STREAMS:
        - NAME: stream_1
          PRESSURE: SIM;PRESSURE_1
          DENSITY: SIM;DENSITY_1
          RATE:
            VALUE: 250 {*} 24
            UNIT: M3_PER_DAY
        - NAME: stream_2
          PRESSURE: 20
          DENSITY: 1000
          RATE:
            VALUE: 600 {*} 24
            UNIT: M3_PER_DAY
    CONSTRAINTS:
      line_1:
        - OUTLET_PRESSURE: 60
          PRESSURE_CONTROL: DOWNSTREAM_CHOKE
      line_2:
        - OUTLET_PRESSURE: 145
          PRESSURE_CONTROL: NONE
"""


def test_individual_streams_give_each_pipeline_its_own_stream(evaluate_model):
    """The first pump recirculates up to its minimum flow of 300 m3/h, where the head is 8750 J/kg."""
    periods = evaluate_model(
        yaml.safe_load(INDIVIDUAL_STREAMS), {"PRESSURE_1": [10.0, 15.0], "DENSITY_1": [1000.0, 800.0]}
    )

    line_2 = PipelineSummary([600.0] * 4, [20.0, 20.0, 145.0, 145.0], [PumpSummary(speed_rpm=2500.0)])
    assert periods == [
        # The head is 87.5 bar for 1000 kg/m3.
        PeriodSummary(
            selected_setting_index=0,
            is_valid=True,
            pipelines=[
                PipelineSummary(
                    [250.0, 300.0, 300.0, 250.0, 250.0],
                    [10.0, 10.0, 97.5, 97.5, 60.0],
                    [PumpSummary(speed_rpm=2000.0)],
                ),
                line_2,
            ],
        ),
        # The head is 70 bar for 800 kg/m3.
        PeriodSummary(
            selected_setting_index=0,
            is_valid=True,
            pipelines=[
                PipelineSummary(
                    [250.0, 300.0, 300.0, 250.0, 250.0],
                    [15.0, 15.0, 85.0, 85.0, 60.0],
                    [PumpSummary(speed_rpm=2000.0)],
                ),
                line_2,
            ],
        ),
    ]
