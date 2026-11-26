import uuid
from datetime import datetime

import pytest

from libecalc.common.time_utils import Period
from libecalc.ecalc_model.equipment.pump_equipment import PumpEquipment
from libecalc.ecalc_model.process.process_pipeline import ProcessUnitConnection
from libecalc.ecalc_model.process.process_units import (
    TimeSeriesChokeProcessUnit,
    TimeSeriesDirectMixerProcessUnit,
    TimeSeriesDirectSplitterProcessUnit,
    TimeSeriesInletProcessUnit,
    TimeSeriesOutletProcessUnit,
    TimeSeriesPumpProcessUnit,
)
from libecalc.ecalc_model.process.pump.liquid_recirculation_loop import LiquidRecirculationLoop
from libecalc.ecalc_model.process.pump.pump_pipeline import PumpPipeline
from libecalc.ecalc_model.validation import InvalidEcalcModelException
from libecalc.process.chart.chart import ChartCurve
from libecalc.process.process_pipeline.process_pipeline import ProcessPipelineId
from libecalc.process.process_pipeline.process_unit import ProcessUnitId


def test_pump_equipment_requires_name():
    with pytest.raises(InvalidEcalcModelException, match="name must not be empty"):
        PumpEquipment(name=" ")


def test_pump_process_unit_holds_pump_data(pump_chart, pump_equipment):
    process_unit_id = ProcessUnitId(uuid.uuid4())

    pump = TimeSeriesPumpProcessUnit(
        pump_chart=pump_chart, pump_equipment_id=pump_equipment.get_id(), process_unit_id=process_unit_id
    )

    assert pump.pump_chart is pump_chart
    assert pump.pump_equipment_id == pump_equipment.get_id()
    assert pump.minimum_flow_rate_m3_per_hour is None
    assert pump.get_id() == process_unit_id


def test_pump_process_unit_rejects_minimum_flow_below_chart(pump_unit_factory):
    with pytest.raises(InvalidEcalcModelException, match="cannot be below the chart's minimum rate"):
        pump_unit_factory(minimum_flow_rate_m3_per_hour=100.0)


def test_pump_process_unit_rejects_non_positive_efficiency(chart_data_factory, pump_equipment):
    chart = chart_data_factory.from_curves(
        curves=[
            ChartCurve(
                speed_rpm=2000.0,
                rate_actual_m3_hour=[200.0, 400.0],
                polytropic_head_joule_per_kg=[9000.0, 8500.0],
                efficiency_fraction=[0.0, 0.7],
            )
        ]
    )

    with pytest.raises(InvalidEcalcModelException, match="efficiency must be greater than 0"):
        TimeSeriesPumpProcessUnit(pump_chart=chart, pump_equipment_id=pump_equipment.get_id())


def test_pump_pipeline_units_in_flow_order(process_units_factory, periods):
    process_units = process_units_factory()
    pipeline = PumpPipeline(name="pump", process_units=process_units, process_periods=periods)

    assert pipeline.get_process_units() == tuple(process_units)


def test_pump_pipeline_allows_several_pumps(process_units_factory, pump_unit_factory, periods):
    process_units = [
        TimeSeriesInletProcessUnit(),
        pump_unit_factory(),
        TimeSeriesChokeProcessUnit(),
        pump_unit_factory(),
        TimeSeriesOutletProcessUnit(),
    ]

    pipeline = PumpPipeline(name="pump", process_units=process_units, process_periods=periods)

    assert pipeline.get_process_units() == tuple(process_units)
    assert len(pipeline.get_process_unit_connections()) == 4


def test_pump_pipeline_connections_chain_units(pump_pipeline_factory):
    pipeline = pump_pipeline_factory()
    unit_ids = [unit.get_id() for unit in pipeline.get_process_units()]

    connections = pipeline.get_process_unit_connections()

    assert [
        (connection.get_from_process_unit_id(), connection.get_to_process_unit_id()) for connection in connections
    ] == list(zip(unit_ids[:-1], unit_ids[1:], strict=True))


def test_pump_pipeline_keeps_given_id(process_units_factory, periods):
    pipeline_id = ProcessPipelineId(uuid.uuid4())

    pipeline = PumpPipeline(
        name="pump", process_units=process_units_factory(), process_periods=periods, process_pipeline_id=pipeline_id
    )

    assert pipeline.get_id() == pipeline_id


def test_pump_pipeline_keeps_given_connections(pump_pipeline_factory, periods):
    original = pump_pipeline_factory()

    rebuilt = PumpPipeline(
        name="pump",
        process_units=original.get_process_units(),
        process_periods=periods,
        process_pipeline_id=original.get_id(),
        process_unit_connections=original.get_process_unit_connections(),
    )

    assert [connection.get_id() for connection in rebuilt.get_process_unit_connections()] == [
        connection.get_id() for connection in original.get_process_unit_connections()
    ]


def test_pump_pipeline_rejects_connections_not_matching_units(pump_pipeline_factory, process_units_factory, periods):
    original = pump_pipeline_factory()

    with pytest.raises(InvalidEcalcModelException, match="must chain the process units"):
        PumpPipeline(
            name="pump",
            process_units=process_units_factory(),
            process_periods=periods,
            process_unit_connections=original.get_process_unit_connections(),
        )


def test_pump_pipeline_rejects_duplicate_connection_ids(pump_pipeline_factory, periods):
    original = pump_pipeline_factory()
    [first, *rest] = original.get_process_unit_connections()
    duplicated_id = [
        ProcessUnitConnection(
            from_process_unit_id=connection.get_from_process_unit_id(),
            to_process_unit_id=connection.get_to_process_unit_id(),
            process_unit_connection_id=first.get_id(),
        )
        for connection in rest
    ]

    with pytest.raises(InvalidEcalcModelException, match="connection ids must be unique"):
        PumpPipeline(
            name="pump",
            process_units=original.get_process_units(),
            process_periods=periods,
            process_unit_connections=[first, *duplicated_id],
        )


@pytest.mark.parametrize(
    "process_units",
    [
        [],
        [TimeSeriesInletProcessUnit(), TimeSeriesChokeProcessUnit(), TimeSeriesOutletProcessUnit()],
    ],
    ids=["empty", "no_pump"],
)
def test_pump_pipeline_requires_a_pump(process_units, periods):
    with pytest.raises(InvalidEcalcModelException, match="at least one pump process unit"):
        PumpPipeline(name="pump", process_units=process_units, process_periods=periods)


def test_pump_pipeline_rejects_shared_unit_id(process_units_factory, periods):
    inlet, _mixer, pump, splitter, choke, outlet = process_units_factory()
    mixer = TimeSeriesDirectMixerProcessUnit(process_unit_id=choke.get_id())

    with pytest.raises(InvalidEcalcModelException, match="process unit ids must be unique"):
        PumpPipeline(name="pump", process_units=[inlet, mixer, pump, splitter, choke, outlet], process_periods=periods)


@pytest.mark.parametrize(
    "process_periods, message",
    [
        ([], "at least one period"),
        (
            [
                Period(datetime(2025, 1, 1), datetime(2026, 1, 1)),
                Period(datetime(2026, 6, 1), datetime(2027, 1, 1)),
            ],
            "must be sequential",
        ),
    ],
)
def test_pump_pipeline_rejects_invalid_periods(process_units_factory, process_periods, message):
    with pytest.raises(InvalidEcalcModelException, match=message):
        PumpPipeline(name="pump", process_units=process_units_factory(), process_periods=process_periods)


def test_pump_pipeline_requires_name(process_units_factory, periods):
    with pytest.raises(InvalidEcalcModelException, match="name must not be empty"):
        PumpPipeline(name="", process_units=process_units_factory(), process_periods=periods)


def test_liquid_recirculation_loop_requires_different_units():
    process_unit_id = ProcessUnitId(uuid.uuid4())

    with pytest.raises(InvalidEcalcModelException, match="mixer and splitter must be different units"):
        LiquidRecirculationLoop(mixer_process_unit_id=process_unit_id, splitter_process_unit_id=process_unit_id)


def test_pump_pipeline_holds_recirculation_loops(pump_pipeline_factory):
    pipeline = pump_pipeline_factory()
    _inlet, mixer, _pump, splitter, _choke, _outlet = pipeline.get_process_units()

    [loop] = pipeline.get_recirculation_loops()

    assert loop.get_mixer_process_unit_id() == mixer.get_id()
    assert loop.get_splitter_process_unit_id() == splitter.get_id()


def test_pump_pipeline_allows_no_recirculation_loop(process_units_factory, periods):
    pipeline = PumpPipeline(name="pump", process_units=process_units_factory(), process_periods=periods)

    assert pipeline.get_recirculation_loops() == ()


def test_pump_pipeline_allows_several_recirculation_loops(pump_unit_factory, periods):
    mixer_a, splitter_a = TimeSeriesDirectMixerProcessUnit(), TimeSeriesDirectSplitterProcessUnit()
    mixer_b, splitter_b = TimeSeriesDirectMixerProcessUnit(), TimeSeriesDirectSplitterProcessUnit()
    loops = [
        LiquidRecirculationLoop(mixer_process_unit_id=mixer_a.get_id(), splitter_process_unit_id=splitter_a.get_id()),
        LiquidRecirculationLoop(mixer_process_unit_id=mixer_b.get_id(), splitter_process_unit_id=splitter_b.get_id()),
    ]

    pipeline = PumpPipeline(
        name="pump",
        process_units=[mixer_a, pump_unit_factory(), splitter_a, mixer_b, pump_unit_factory(), splitter_b],
        process_periods=periods,
        recirculation_loops=loops,
    )

    assert pipeline.get_recirculation_loops() == tuple(loops)


def test_pump_pipeline_rejects_duplicate_recirculation_loop_ids(pump_pipeline_factory, periods):
    original = pump_pipeline_factory()
    [loop] = original.get_recirculation_loops()

    with pytest.raises(InvalidEcalcModelException, match="recirculation loop ids must be unique"):
        PumpPipeline(
            name="pump",
            process_units=original.get_process_units(),
            process_periods=periods,
            recirculation_loops=[loop, loop],
        )


@pytest.mark.parametrize(
    "mixer_index, splitter_index, message",
    [
        (4, 3, "mixer .* must be a direct mixer"),
        (1, 4, "splitter .* must be a direct splitter"),
    ],
    ids=["mixer_not_a_mixer", "splitter_not_a_splitter"],
)
def test_pump_pipeline_rejects_recirculation_loop_on_wrong_unit_type(
    process_units_factory, periods, mixer_index, splitter_index, message
):
    process_units = process_units_factory()

    with pytest.raises(InvalidEcalcModelException, match=message):
        PumpPipeline(
            name="pump",
            process_units=process_units,
            process_periods=periods,
            recirculation_loops=[
                LiquidRecirculationLoop(
                    mixer_process_unit_id=process_units[mixer_index].get_id(),
                    splitter_process_unit_id=process_units[splitter_index].get_id(),
                )
            ],
        )


def test_pump_pipeline_rejects_recirculation_loop_outside_pipeline(process_units_factory, periods):
    process_units = process_units_factory()

    with pytest.raises(InvalidEcalcModelException, match="must be a direct mixer in the pipeline"):
        PumpPipeline(
            name="pump",
            process_units=process_units,
            process_periods=periods,
            recirculation_loops=[
                LiquidRecirculationLoop(
                    mixer_process_unit_id=TimeSeriesDirectMixerProcessUnit().get_id(),
                    splitter_process_unit_id=process_units[3].get_id(),
                )
            ],
        )


def test_pump_pipeline_rejects_recirculation_loop_with_splitter_upstream(pump_unit_factory, periods):
    splitter, pump, mixer = (
        TimeSeriesDirectSplitterProcessUnit(),
        pump_unit_factory(),
        TimeSeriesDirectMixerProcessUnit(),
    )

    with pytest.raises(InvalidEcalcModelException, match="mixer must be upstream of its splitter"):
        PumpPipeline(
            name="pump",
            process_units=[splitter, pump, mixer],
            process_periods=periods,
            recirculation_loops=[
                LiquidRecirculationLoop(
                    mixer_process_unit_id=mixer.get_id(), splitter_process_unit_id=splitter.get_id()
                )
            ],
        )


def test_pump_pipeline_rejects_same_pump_twice(pump_unit_factory, pump_equipment, periods):
    pumps = [pump_unit_factory(pump_equipment_id=pump_equipment.get_id()) for _ in range(2)]

    with pytest.raises(InvalidEcalcModelException, match="pumps must be unique"):
        PumpPipeline(name="pump", process_units=pumps, process_periods=periods)
