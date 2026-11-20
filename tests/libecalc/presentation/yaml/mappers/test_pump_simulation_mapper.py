from io import StringIO

import pytest
import yaml

from libecalc.ecalc_model.process.process_units import (
    TimeSeriesChokeProcessUnit,
    TimeSeriesDirectMixerProcessUnit,
    TimeSeriesDirectSplitterProcessUnit,
    TimeSeriesInletProcessUnit,
    TimeSeriesOutletProcessUnit,
    TimeSeriesPressureDropperProcessUnit,
    TimeSeriesPumpProcessUnit,
)
from libecalc.ecalc_model.process.pump.pump_simulation import (
    PumpCommonStreamDistributionConfig,
    PumpIndividualStreamDistributionConfig,
)
from libecalc.ecalc_model.timeline_event import TimelineEventType
from libecalc.expression import Expression
from libecalc.presentation.yaml.model_validation_exception import ModelValidationException
from libecalc.presentation.yaml.yaml_entities import MemoryResource, ResourceStream
from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.components.yaml_expression_type import YamlExpressionType
from libecalc.presentation.yaml.yaml_types.pump.yaml_liquid_stream import YamlLiquidInletStream
from libecalc.presentation.yaml.yaml_types.pump.yaml_pump_model import YamlPumpModel
from libecalc.presentation.yaml.yaml_types.pump.yaml_pump_simulation import YamlPumpPressureControl
from libecalc.presentation.yaml.yaml_types.yaml_variable import YamlSingleVariable
from libecalc.testing.energy_builders import YamlFileBuilder
from libecalc.testing.process_builders import YamlDefinitionsBuilder, YamlTimelineBuilder, YamlTimelineEventBuilder
from libecalc.testing.pump_builders import (
    YamlLiquidInletStreamBuilder,
    YamlLiquidStreamRateBuilder,
    YamlPumpBuilder,
    YamlPumpChartBuilder,
    YamlPumpCommonStreamDistributionBuilder,
    YamlPumpCurveBuilder,
    YamlPumpModelBuilder,
    YamlPumpPipelineBuilder,
    YamlPumpSimulationBuilder,
)
from libecalc.testing.yaml_builder import YamlAssetBuilder

PUMP_A = "pump_a"
PUMP_B = "pump_b"
PUMP_C = "pump_c"
LINE_A = "line_a"
LINE_B = "line_b"
PUMP_MODEL_A = "pump_model_a"
PUMP_MODEL_B = "pump_model_b"
CHART_FILE_NAME = "pump_chart.csv"

_CURVE = YamlPumpCurveBuilder().with_test_data()
CHART_FILE = MemoryResource(headers=["RATE", "HEAD", "EFFICIENCY"], data=[_CURVE.rate, _CURVE.head, _CURVE.efficiency])


def _dump(model: YamlBase) -> dict:
    return model.model_dump(mode="json", exclude_unset=True, by_alias=True)


def _pump_model(minimum_flow_rate: float | None = None) -> YamlPumpModel:
    return YamlPumpModelBuilder().with_test_data().with_minimum_flow_rate(minimum_flow_rate).validate()


def _stream(rate: YamlExpressionType = "$var.rate") -> YamlLiquidInletStream:
    return (
        YamlLiquidInletStreamBuilder()
        .with_test_data()
        .with_name("inlet")
        .with_rate(YamlLiquidStreamRateBuilder().with_test_data().with_value(rate).validate())
        .validate()
    )


def _model_data() -> dict:
    file_chart = YamlPumpChartBuilder().with_curves(YamlFileBuilder().with_file(CHART_FILE_NAME).validate()).validate()
    line_a = YamlPumpPipelineBuilder().with_name(LINE_A).with_pump_item(PUMP_A, PUMP_MODEL_A).validate()
    line_b = (
        YamlPumpPipelineBuilder()
        .with_name(LINE_B)
        .with_pressure_dropper_item(4)
        .with_pump_item(PUMP_B, PUMP_MODEL_B)
        .validate()
    )
    simulation = (
        YamlPumpSimulationBuilder()
        .with_name("pump_simulation")
        .with_pipeline(line_a, outlet_pressure=240)
        .with_pipeline(line_b, outlet_pressure=190, pressure_control=YamlPumpPressureControl.DOWNSTREAM_CHOKE)
        .with_stream_distribution(
            YamlPumpCommonStreamDistributionBuilder()
            .with_inlet_stream(_stream())
            .with_rate_fractions([[1, 0], [0.5, 0.5]])
            .validate()
        )
        .validate()
    )
    asset = (
        YamlAssetBuilder()
        .with_start("2020-01-01")
        .with_end("2022-01-01")
        .with_variables({"rate": YamlSingleVariable(value=Expression.validator(12000))})
        .with_timeline(
            YamlTimelineBuilder()
            .with_event(
                "event",
                YamlTimelineEventBuilder().with_type(TimelineEventType.OTHER).with_from_when("2021-01-01").validate(),
            )
            .validate()
        )
        .with_definitions(
            YamlDefinitionsBuilder()
            .with_pump_model(PUMP_MODEL_A, _pump_model(minimum_flow_rate=300))
            .with_pump_model(PUMP_MODEL_B, YamlPumpModelBuilder().with_chart(file_chart).validate())
            .validate()
        )
        .with_pumps(
            [
                YamlPumpBuilder().with_name(PUMP_A).validate(),
                YamlPumpBuilder().with_name(PUMP_B).with_alias("Pump B").validate(),
            ]
        )
        .with_pump_pipelines([line_a, line_b])
        .with_pump_simulations([simulation])
        .validate()
    )
    return _dump(asset)


@pytest.fixture
def model_factory(yaml_model_factory):
    def create(model_data: dict | None = None):
        return yaml_model_factory(
            configuration=ResourceStream(name="pump_model", stream=StringIO(yaml.dump(model_data or _model_data()))),
            resources={CHART_FILE_NAME: CHART_FILE},
            nextgen=True,
        )

    return create


def test_maps_pump_equipment(model_factory):
    pumps = model_factory().get_pumps()

    assert [(pump.name, pump.alias) for pump in pumps] == [(PUMP_A, None), (PUMP_B, "Pump B")]


def test_maps_pump_pipelines(model_factory):
    model = model_factory()
    pump_equipment_ids = {pump.name: pump.get_id() for pump in model.get_pumps()}

    (line_a, line_b), _ = model.get_pump_simulations()

    assert line_a.get_name() == LINE_A
    assert [type(unit) for unit in line_b.get_process_units()] == [
        TimeSeriesInletProcessUnit,
        TimeSeriesPressureDropperProcessUnit,
        TimeSeriesDirectMixerProcessUnit,
        TimeSeriesPumpProcessUnit,
        TimeSeriesDirectSplitterProcessUnit,
        TimeSeriesChokeProcessUnit,
        TimeSeriesOutletProcessUnit,
    ]
    assert [type(unit) for unit in line_a.get_process_units()] == [
        TimeSeriesInletProcessUnit,
        TimeSeriesDirectMixerProcessUnit,
        TimeSeriesPumpProcessUnit,
        TimeSeriesDirectSplitterProcessUnit,
        TimeSeriesOutletProcessUnit,
    ]
    pump_a_pump = line_a.get_process_units()[2]
    pump_b_pump = line_b.get_process_units()[3]
    assert pump_a_pump.pump_equipment_id == pump_equipment_ids[PUMP_A]
    assert pump_a_pump.minimum_flow_rate_m3_per_hour == 300
    assert pump_b_pump.pump_equipment_id == pump_equipment_ids[PUMP_B]
    assert pump_b_pump.minimum_flow_rate_m3_per_hour is None
    assert len(pump_b_pump.pump_chart.get_original_curves()) == 1

    [loop] = line_b.get_recirculation_loops()
    _inlet, _dropper, mixer, _pump, splitter, _choke, _outlet = line_b.get_process_units()
    assert loop.get_mixer_process_unit_id() == mixer.get_id()
    assert loop.get_splitter_process_unit_id() == splitter.get_id()


def test_maps_pump_simulation(model_factory):
    pump_pipelines, [simulation] = model_factory().get_pump_simulations()
    line_a, line_b = pump_pipelines

    assert simulation.get_name() == "pump_simulation"
    assert simulation.get_pump_pipeline_ids() == [line_a.get_id(), line_b.get_id()]
    problems = simulation.get_pump_problems()
    [pump_a_problem] = problems[line_a.get_id()]
    [pump_b_problem] = problems[line_b.get_id()]
    assert pump_a_problem.get_pump_pipeline_id() == line_a.get_id()
    assert pump_a_problem.get_constraint().outlet_pressure.get_masked_values() == [240.0, 240.0]
    assert pump_b_problem.get_constraint().outlet_pressure.get_masked_values() == [190.0, 190.0]

    choke, _outlet = line_b.get_process_units()[-2:]
    constraint = pump_b_problem.get_constraint()
    assert constraint.target_process_unit_id == choke.get_id()
    assert constraint.target_process_connection_id == line_b.get_process_unit_connections()[-1].get_id()
    assert pump_b_problem.get_choke_pressure_control_id() == choke.get_id()

    pump_a_splitter = line_a.get_process_units()[3]
    assert pump_a_problem.get_constraint().target_process_unit_id == pump_a_splitter.get_id()
    assert (
        pump_a_problem.get_constraint().target_process_connection_id
        == line_a.get_process_unit_connections()[-1].get_id()
    )
    assert pump_a_problem.get_choke_pressure_control_id() is None

    stream_distribution = simulation.get_stream_distribution()
    assert isinstance(stream_distribution, PumpCommonStreamDistributionConfig)
    assert stream_distribution.inlet_stream.volumetric_rate_m3_per_day.get_stream_day_values() == [12000.0, 12000.0]
    assert [setting.get_rate_fraction_values() for setting in stream_distribution.settings] == [
        [[1.0, 1.0], [0.0, 0.0]],
        [[0.5, 0.5], [0.5, 0.5]],
    ]

    pressure_dropper = line_b.get_process_units()[1]
    configurations = simulation.get_process_configurations()
    assert set(configurations) == {line_b.get_id()}
    assert configurations[line_b.get_id()][pressure_dropper.get_id()].pressure_drop_in_bara.get_masked_values() == [
        4.0,
        4.0,
    ]


def test_maps_individual_streams(model_factory):
    model_data = _model_data()
    model_data["PUMP_SIMULATIONS"][0]["STREAM_DISTRIBUTION"] = {
        "METHOD": "INDIVIDUAL_STREAMS",
        "INLET_STREAMS": [_dump(_stream(rate=100)), _dump(_stream(rate=200))],
    }

    _, [simulation] = model_factory(model_data).get_pump_simulations()

    stream_distribution = simulation.get_stream_distribution()
    assert isinstance(stream_distribution, PumpIndividualStreamDistributionConfig)
    assert [
        stream.volumetric_rate_m3_per_day.get_stream_day_values() for stream in stream_distribution.inlet_streams
    ] == [
        [100.0, 100.0],
        [200.0, 200.0],
    ]


def test_inline_pump_model(model_factory):
    model_data = _model_data()
    model_data["PUMP_PIPELINES"][0]["PROCESS_UNITS"][0]["MODEL"] = _dump(_pump_model(minimum_flow_rate=400))

    (line_a, _), _ = model_factory(model_data).get_pump_simulations()

    assert line_a.get_process_units()[2].minimum_flow_rate_m3_per_hour == 400


def test_no_pump_simulations(model_factory):
    model_data = _model_data()
    del model_data["PUMP_SIMULATIONS"]

    assert model_factory(model_data).get_pump_simulations() == ([], [])


def _invalid(model_data: dict, model_factory) -> str:
    with pytest.raises(ModelValidationException) as exc_info:
        model_factory(model_data).get_pump_simulations()
    return "\n".join(error.message for error in exc_info.value.errors())


def test_rejects_unknown_pump(model_factory):
    model_data = _model_data()
    model_data["PUMPS"] = [_dump(YamlPumpBuilder().with_name(PUMP_A).validate())]

    assert f"Pump '{PUMP_B}' in pump pipeline '{LINE_B}' is not defined in PUMPS." in _invalid(
        model_data, model_factory
    )


def test_rejects_unknown_target(model_factory):
    model_data = _model_data()
    model_data["PUMP_SIMULATIONS"][0]["TARGETS"] = [LINE_A, "unknown_line"]

    assert "unknown_line" in _invalid(model_data, model_factory)


def test_rejects_constraint_for_other_than_target(model_factory):
    model_data = _model_data()
    simulation = model_data["PUMP_SIMULATIONS"][0]
    simulation["TARGETS"] = [LINE_A]
    simulation["STREAM_DISTRIBUTION"]["SETTINGS"] = [{"RATE_FRACTIONS": [1]}]

    assert f"CONSTRAINTS for '{LINE_B}', which is not one of its TARGETS" in _invalid(model_data, model_factory)


def _two_pump_model_data(constraints: list[dict]) -> dict:
    model_data = _model_data()
    model_data["PUMPS"].append(_dump(YamlPumpBuilder().with_name(PUMP_C).validate()))
    model_data["PUMP_PIPELINES"][0] = _dump(
        YamlPumpPipelineBuilder()
        .with_name(LINE_A)
        .with_pump_item(PUMP_A, PUMP_MODEL_A)
        .with_pressure_dropper_item(2)
        .with_pump_item(PUMP_C, PUMP_MODEL_A)
        .validate()
    )
    model_data["PUMP_SIMULATIONS"][0]["CONSTRAINTS"][LINE_A] = constraints
    return model_data


def test_maps_one_problem_per_pump_in_a_pipeline(model_factory):
    model_data = _two_pump_model_data(
        [
            {"OUTLET_PRESSURE": 240, "PRESSURE_CONTROL": "DOWNSTREAM_CHOKE"},
            {"PROCESS_UNIT": PUMP_A, "OUTLET_PRESSURE": 120, "PRESSURE_CONTROL": "DOWNSTREAM_CHOKE"},
        ],
    )

    (line_a, _), [simulation] = model_factory(model_data).get_pump_simulations()

    units = line_a.get_process_units()
    assert [type(unit) for unit in units] == [
        TimeSeriesInletProcessUnit,
        TimeSeriesDirectMixerProcessUnit,
        TimeSeriesPumpProcessUnit,
        TimeSeriesDirectSplitterProcessUnit,
        TimeSeriesChokeProcessUnit,
        TimeSeriesPressureDropperProcessUnit,
        TimeSeriesDirectMixerProcessUnit,
        TimeSeriesPumpProcessUnit,
        TimeSeriesDirectSplitterProcessUnit,
        TimeSeriesChokeProcessUnit,
        TimeSeriesOutletProcessUnit,
    ]
    assert len(line_a.get_recirculation_loops()) == 2
    first_choke, second_choke = units[4], units[9]
    connections = line_a.get_process_unit_connections()

    first, second = simulation.get_pump_problems()[line_a.get_id()]
    assert first.get_constraint().outlet_pressure.get_masked_values() == [120.0, 120.0]
    assert first.get_constraint().target_process_unit_id == first_choke.get_id()
    assert first.get_constraint().target_process_connection_id == connections[4].get_id()
    assert first.get_choke_pressure_control_id() == first_choke.get_id()
    assert second.get_constraint().outlet_pressure.get_masked_values() == [240.0, 240.0]
    assert second.get_constraint().target_process_unit_id == second_choke.get_id()
    assert second.get_choke_pressure_control_id() == second_choke.get_id()


def test_maps_pressure_control_per_pump(model_factory):
    model_data = _two_pump_model_data(
        [
            {"OUTLET_PRESSURE": 240, "PRESSURE_CONTROL": "NONE"},
            {"PROCESS_UNIT": PUMP_A, "OUTLET_PRESSURE": 120, "PRESSURE_CONTROL": "DOWNSTREAM_CHOKE"},
        ],
    )

    (line_a, _), [simulation] = model_factory(model_data).get_pump_simulations()

    units = line_a.get_process_units()
    assert [type(unit) for unit in units] == [
        TimeSeriesInletProcessUnit,
        TimeSeriesDirectMixerProcessUnit,
        TimeSeriesPumpProcessUnit,
        TimeSeriesDirectSplitterProcessUnit,
        TimeSeriesChokeProcessUnit,
        TimeSeriesPressureDropperProcessUnit,
        TimeSeriesDirectMixerProcessUnit,
        TimeSeriesPumpProcessUnit,
        TimeSeriesDirectSplitterProcessUnit,
        TimeSeriesOutletProcessUnit,
    ]
    first_choke, second_splitter = units[4], units[8]
    first, second = simulation.get_pump_problems()[line_a.get_id()]
    assert first.get_constraint().target_process_unit_id == first_choke.get_id()
    assert first.get_choke_pressure_control_id() == first_choke.get_id()
    assert second.get_constraint().target_process_unit_id == second_splitter.get_id()
    assert second.get_constraint().target_process_connection_id == line_a.get_process_unit_connections()[-1].get_id()
    assert second.get_choke_pressure_control_id() is None


def test_requires_a_constraint_for_every_pump(model_factory):
    model_data = _two_pump_model_data([{"OUTLET_PRESSURE": 240}])

    assert f"must have one constraint per pump. Missing a constraint for: {PUMP_A}." in _invalid(
        model_data, model_factory
    )


def test_requires_a_constraint_for_the_pipeline(model_factory):
    model_data = _model_data()
    model_data["PUMP_SIMULATIONS"][0]["CONSTRAINTS"][LINE_B] = []

    assert f"Missing a constraint for: {PUMP_B}." in _invalid(model_data, model_factory)


@pytest.mark.parametrize(
    "constraints",
    [
        [{"OUTLET_PRESSURE": 240}, {"OUTLET_PRESSURE": 200}],
        [{"OUTLET_PRESSURE": 240}, {"PROCESS_UNIT": PUMP_C, "OUTLET_PRESSURE": 200}],
    ],
    ids=["two_without_process_unit", "explicit_last_pump_and_outlet"],
)
def test_rejects_more_than_one_constraint_per_pump(model_factory, constraints):
    assert f"more than one constraint for pump '{PUMP_C}'" in _invalid(_two_pump_model_data(constraints), model_factory)


def test_rejects_constraint_for_unknown_process_unit(model_factory):
    model_data = _two_pump_model_data(
        [{"OUTLET_PRESSURE": 240}, {"PROCESS_UNIT": PUMP_B, "OUTLET_PRESSURE": 120}],
    )

    assert f"PROCESS_UNIT '{PUMP_B}', which is not a pump in the pipeline" in _invalid(model_data, model_factory)


def test_reports_domain_validation_errors(model_factory):
    model_data = _model_data()
    model_data["PUMP_SIMULATIONS"][0]["STREAM_DISTRIBUTION"]["SETTINGS"] = [{"RATE_FRACTIONS": [1]}]

    assert "Specify one stream per pump pipeline" in _invalid(model_data, model_factory)


def test_rejects_unknown_pump_model(model_factory):
    model_data = _model_data()
    model_data["PUMP_PIPELINES"][0]["PROCESS_UNITS"][0]["MODEL"] = "unknown_model"

    assert "unknown_model" in _invalid(model_data, model_factory)


def test_validate_nextgen_includes_pump_simulations(model_factory):
    model_data = _model_data()
    model_data["PUMPS"] = [_dump(YamlPumpBuilder().with_name(PUMP_A).validate())]

    with pytest.raises(ModelValidationException, match="is not defined in PUMPS"):
        model_factory(model_data).validate_nextgen()
