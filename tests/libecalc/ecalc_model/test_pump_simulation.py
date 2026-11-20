import uuid

import pytest

from libecalc.ecalc_model.process.pump.pump_simulation import (
    PumpCommonStreamDistributionConfig,
    PumpCommonStreamSettings,
    PumpIndividualStreamDistributionConfig,
    PumpProblem,
    PumpProblemId,
    PumpSimulation,
)
from libecalc.ecalc_model.time_series_configuration import TimeSeriesPressureDropperConfiguration
from libecalc.ecalc_model.validation import InvalidEcalcModelException
from libecalc.presentation.yaml.domain.expression_time_series_flow_rate import InvalidFlowRateException
from libecalc.process.process_pipeline.process_pipeline import ProcessPipelineId
from libecalc.process.process_pipeline.process_unit import ProcessUnitId
from libecalc.process.pump.pump_process_simulation import PumpProcessSimulationId
from libecalc.process.stream_distribution.common_stream_distribution import Overflow


@pytest.fixture
def pump_pipeline(pump_pipeline_factory):
    return pump_pipeline_factory()


@pytest.fixture
def pump_problem(pump_problem_factory, pump_pipeline):
    return pump_problem_factory(pump_pipeline)


@pytest.fixture
def common_distribution_factory(liquid_stream_factory, expression_factory):
    def create(fractions, overflow=(), inlet_stream=None) -> PumpCommonStreamDistributionConfig:
        return PumpCommonStreamDistributionConfig(
            inlet_stream=inlet_stream or liquid_stream_factory(),
            settings=[
                PumpCommonStreamSettings(
                    rate_fractions=[expression_factory(fraction) for fraction in fractions],
                    overflow=list(overflow),
                )
            ],
        )

    return create


def _by_pipeline(*pump_problems: PumpProblem) -> dict[ProcessPipelineId, list[PumpProblem]]:
    grouped: dict[ProcessPipelineId, list[PumpProblem]] = {}
    for pump_problem in pump_problems:
        grouped.setdefault(pump_problem.get_pump_pipeline_id(), []).append(pump_problem)
    return grouped


def _individual(*inlet_streams) -> PumpIndividualStreamDistributionConfig:
    return PumpIndividualStreamDistributionConfig(inlet_streams=list(inlet_streams))


def test_pump_problem_references_pipeline(pump_problem, pump_pipeline):
    choke = pump_pipeline.get_process_units()[-2]
    constraint = pump_problem.get_constraint()

    assert pump_problem.get_pump_pipeline_id() == pump_pipeline.get_id()
    assert constraint.target_process_unit_id == choke.get_id()
    assert constraint.target_process_connection_id == pump_pipeline.get_process_unit_connections()[-1].get_id()
    assert constraint.outlet_pressure.get_masked_values() == [150.0, 200.0]


def test_pump_problem_keeps_given_id(pump_problem):
    pump_problem_id = PumpProblemId(uuid.uuid4())

    problem = PumpProblem(
        constraint=pump_problem.get_constraint(),
        pump_pipeline_id=pump_problem.get_pump_pipeline_id(),
        pump_problem_id=pump_problem_id,
    )

    assert problem.get_id() == pump_problem_id


def test_pump_problem_choke_pressure_control_id_is_optional(pump_problem, pump_pipeline):
    choke = pump_pipeline.get_process_units()[-2]

    with_choke = PumpProblem(
        constraint=pump_problem.get_constraint(),
        pump_pipeline_id=pump_problem.get_pump_pipeline_id(),
        choke_pressure_control_id=choke.get_id(),
    )

    assert pump_problem.get_choke_pressure_control_id() is None
    assert with_choke.get_choke_pressure_control_id() == choke.get_id()


@pytest.mark.parametrize(
    "pressure, density, message",
    [
        (0, 1010, "pressure \\[bara\\] must be greater than 0"),
        (10, 0, "density \\[kg/m3\\] must be greater than 0"),
    ],
)
def test_liquid_stream_requires_positive_pressure_and_density(liquid_stream_factory, pressure, density, message):
    with pytest.raises(InvalidEcalcModelException, match=message):
        liquid_stream_factory(pressure=pressure, density=density)


def test_liquid_stream_rejects_negative_rate(liquid_stream_factory):
    with pytest.raises(InvalidFlowRateException):
        liquid_stream_factory(rate=-1)


def test_pump_simulation_holds_stream_distribution_and_problems(liquid_stream_factory, pump_problem, periods):
    stream_distribution = _individual(liquid_stream_factory())
    simulation = PumpSimulation(
        name="water_injection",
        stream_distribution=stream_distribution,
        pump_problems=_by_pipeline(pump_problem),
        process_periods=periods,
    )

    assert simulation.get_name() == "water_injection"
    assert simulation.get_stream_distribution() == stream_distribution
    assert simulation.get_pump_problems() == {pump_problem.get_pump_pipeline_id(): [pump_problem]}
    assert simulation.get_pump_pipeline_ids() == [pump_problem.get_pump_pipeline_id()]
    assert simulation.get_process_periods() == periods
    [stream] = simulation.get_inlet_streams()
    assert stream.volumetric_rate_m3_per_day.get_stream_day_values() == [12000.0, 12000.0]
    assert stream.pressure_bara.get_masked_values() == [10.0, 10.0]
    assert stream.density_kg_per_m3.get_masked_values() == [1010.0, 1010.0]


def test_pump_simulation_common_stream_distribution(
    pump_pipeline_factory, pump_problem_factory, common_distribution_factory, periods
):
    pipelines = [pump_pipeline_factory(name) for name in ("pump_a", "pump_b")]
    overflow = Overflow(from_id=pipelines[0].get_id(), to_id=pipelines[1].get_id())
    stream_distribution = common_distribution_factory(fractions=[0.6, 0.4], overflow=[overflow])

    simulation = PumpSimulation(
        name="water_injection",
        stream_distribution=stream_distribution,
        pump_problems=_by_pipeline(*(pump_problem_factory(pipeline) for pipeline in pipelines)),
        process_periods=periods,
    )

    assert simulation.get_inlet_streams() == [stream_distribution.inlet_stream]
    [stream_settings] = simulation.get_stream_distribution().settings
    assert stream_settings.get_rate_fraction_values() == [[0.6, 0.6], [0.4, 0.4]]
    assert stream_settings.overflow == [overflow]


def test_pump_simulation_ids(liquid_stream_factory, pump_problem, periods):
    pump_simulation_id = PumpProcessSimulationId(uuid.uuid4())

    given = PumpSimulation(
        name="a",
        stream_distribution=_individual(liquid_stream_factory()),
        pump_problems=_by_pipeline(pump_problem),
        process_periods=periods,
        pump_simulation_id=pump_simulation_id,
    )
    generated = PumpSimulation(
        name="b",
        stream_distribution=_individual(liquid_stream_factory()),
        pump_problems=_by_pipeline(pump_problem),
        process_periods=periods,
    )

    assert given.get_id() == pump_simulation_id
    assert generated.get_id() != given.get_id()


def test_pump_simulation_requires_problems(liquid_stream_factory, periods):
    with pytest.raises(InvalidEcalcModelException, match="at least one pump pipeline"):
        PumpSimulation(
            name="a",
            stream_distribution=_individual(liquid_stream_factory()),
            pump_problems={},
            process_periods=periods,
        )


def test_pump_simulation_requires_one_stream_per_problem(liquid_stream_factory, pump_problem, periods):
    with pytest.raises(InvalidEcalcModelException, match="Specify one stream per pump pipeline"):
        PumpSimulation(
            name="a",
            stream_distribution=_individual(liquid_stream_factory(), liquid_stream_factory()),
            pump_problems=_by_pipeline(pump_problem),
            process_periods=periods,
        )


def test_pump_simulation_allows_several_problems_in_one_pipeline(
    liquid_stream_factory, pump_problem_factory, pump_pipeline, periods
):
    problems = [pump_problem_factory(pump_pipeline), pump_problem_factory(pump_pipeline)]

    simulation = PumpSimulation(
        name="a",
        stream_distribution=_individual(liquid_stream_factory()),
        pump_problems={pump_pipeline.get_id(): problems},
        process_periods=periods,
    )

    assert simulation.get_pump_problems() == {pump_pipeline.get_id(): problems}


def test_pump_simulation_requires_problems_for_each_pipeline(liquid_stream_factory, pump_pipeline, periods):
    with pytest.raises(InvalidEcalcModelException, match="at least one pump problem for pump pipeline"):
        PumpSimulation(
            name="a",
            stream_distribution=_individual(liquid_stream_factory()),
            pump_problems={pump_pipeline.get_id(): []},
            process_periods=periods,
        )


def test_pump_simulation_rejects_problem_under_other_pipeline(liquid_stream_factory, pump_problem, periods):
    with pytest.raises(InvalidEcalcModelException, match="but is given for pump pipeline"):
        PumpSimulation(
            name="a",
            stream_distribution=_individual(liquid_stream_factory()),
            pump_problems={ProcessPipelineId(uuid.uuid4()): [pump_problem]},
            process_periods=periods,
        )


def test_pump_simulation_rejects_duplicate_problem_ids(liquid_stream_factory, pump_problem, periods):
    with pytest.raises(InvalidEcalcModelException, match="pump problem ids must be unique"):
        PumpSimulation(
            name="a",
            stream_distribution=_individual(liquid_stream_factory()),
            pump_problems={pump_problem.get_pump_pipeline_id(): [pump_problem, pump_problem]},
            process_periods=periods,
        )


def test_pump_simulation_checks_outlet_pressure_of_every_problem_in_running_pipeline(
    liquid_stream_factory, pump_problem_factory, pump_pipeline, periods
):
    with pytest.raises(InvalidEcalcModelException, match="outlet pressure \\[bara\\] must be greater than 0"):
        PumpSimulation(
            name="a",
            stream_distribution=_individual(liquid_stream_factory(rate=100)),
            pump_problems=_by_pipeline(
                pump_problem_factory(pump_pipeline), pump_problem_factory(pump_pipeline, outlet_pressure=0)
            ),
            process_periods=periods,
        )


def test_pump_simulation_rejects_other_periods(liquid_stream_factory, pump_problem, periods):
    with pytest.raises(InvalidEcalcModelException, match="same periods as the simulation"):
        PumpSimulation(
            name="a",
            stream_distribution=_individual(liquid_stream_factory()),
            pump_problems=_by_pipeline(pump_problem),
            process_periods=periods[:1],
        )


def test_pump_simulation_requires_positive_outlet_pressure_when_running(
    liquid_stream_factory, pump_problem_factory, pump_pipeline, periods
):
    with pytest.raises(InvalidEcalcModelException, match="outlet pressure \\[bara\\] must be greater than 0"):
        PumpSimulation(
            name="a",
            stream_distribution=_individual(liquid_stream_factory(rate=100)),
            pump_problems=_by_pipeline(pump_problem_factory(pump_pipeline, outlet_pressure=0)),
            process_periods=periods,
        )


def test_pump_simulation_allows_zero_outlet_pressure_when_not_running(
    liquid_stream_factory, pump_problem_factory, pump_pipeline, periods
):
    PumpSimulation(
        name="a",
        stream_distribution=_individual(liquid_stream_factory(rate=0)),
        pump_problems=_by_pipeline(pump_problem_factory(pump_pipeline, outlet_pressure=0)),
        process_periods=periods,
    )


def test_pump_simulation_common_allows_zero_outlet_pressure_without_rate_fraction(
    pump_pipeline_factory, pump_problem_factory, common_distribution_factory, periods
):
    pipelines = [pump_pipeline_factory(name) for name in ("pump_a", "pump_b")]

    PumpSimulation(
        name="a",
        stream_distribution=common_distribution_factory(fractions=[1.0, 0.0]),
        pump_problems=_by_pipeline(
            pump_problem_factory(pipelines[0]), pump_problem_factory(pipelines[1], outlet_pressure=0)
        ),
        process_periods=periods,
    )


def test_pump_simulation_common_requires_outlet_pressure_for_overflow_target(
    pump_pipeline_factory, pump_problem_factory, common_distribution_factory, periods
):
    pipelines = [pump_pipeline_factory(name) for name in ("pump_a", "pump_b")]
    overflow = Overflow(from_id=pipelines[0].get_id(), to_id=pipelines[1].get_id())

    with pytest.raises(InvalidEcalcModelException, match="outlet pressure \\[bara\\] must be greater than 0"):
        PumpSimulation(
            name="a",
            stream_distribution=common_distribution_factory(fractions=[1.0, 0.0], overflow=[overflow]),
            pump_problems=_by_pipeline(
                pump_problem_factory(pipelines[0]), pump_problem_factory(pipelines[1], outlet_pressure=0)
            ),
            process_periods=periods,
        )


def test_pump_simulation_rejects_overflow_to_unknown_pipeline(
    pump_pipeline_factory, pump_problem_factory, common_distribution_factory, periods
):
    pipelines = [pump_pipeline_factory(name) for name in ("pump_a", "pump_b")]
    overflow = Overflow(from_id=pipelines[0].get_id(), to_id=ProcessPipelineId(uuid.uuid4()))

    with pytest.raises(InvalidEcalcModelException, match="overflow must refer to its own pump pipelines"):
        PumpSimulation(
            name="a",
            stream_distribution=common_distribution_factory(fractions=[0.5, 0.5], overflow=[overflow]),
            pump_problems=_by_pipeline(*(pump_problem_factory(pipeline) for pipeline in pipelines)),
            process_periods=periods,
        )


@pytest.mark.parametrize(
    "fractions, message",
    [
        ([], "at least one rate fraction"),
        ([1.2, 0.0], "between 0 and 1"),
        ([-0.1, 0.5], "between 0 and 1"),
        ([0.7, 0.7], "must not sum to more than 1"),
    ],
)
def test_common_stream_settings_rejects_invalid_rate_fractions(common_distribution_factory, fractions, message):
    with pytest.raises(InvalidEcalcModelException, match=message):
        common_distribution_factory(fractions=fractions)


def test_common_stream_settings_rejects_overflow_to_itself(common_distribution_factory):
    pipeline_id = ProcessPipelineId(uuid.uuid4())

    with pytest.raises(InvalidEcalcModelException, match="another pipeline"):
        common_distribution_factory(fractions=[1.0], overflow=[Overflow(from_id=pipeline_id, to_id=pipeline_id)])


def test_common_stream_settings_rejects_cyclic_overflow(common_distribution_factory):
    a, b, c = (ProcessPipelineId(uuid.uuid4()) for _ in range(3))

    with pytest.raises(InvalidEcalcModelException, match="must not be cyclic"):
        common_distribution_factory(
            fractions=[0.4, 0.3, 0.3],
            overflow=[Overflow(from_id=a, to_id=b), Overflow(from_id=b, to_id=c), Overflow(from_id=c, to_id=a)],
        )


def test_common_stream_settings_rejects_several_overflows_from_one_pipeline(common_distribution_factory):
    a, b, c = (ProcessPipelineId(uuid.uuid4()) for _ in range(3))

    with pytest.raises(InvalidEcalcModelException, match="overflow sources must be unique"):
        common_distribution_factory(
            fractions=[0.4, 0.3, 0.3], overflow=[Overflow(from_id=a, to_id=b), Overflow(from_id=a, to_id=c)]
        )


def test_common_stream_distribution_requires_settings(liquid_stream_factory):
    with pytest.raises(InvalidEcalcModelException, match="at least one setting"):
        PumpCommonStreamDistributionConfig(inlet_stream=liquid_stream_factory(), settings=[])


def test_common_stream_distribution_requires_same_number_of_fractions(liquid_stream_factory, expression_factory):
    with pytest.raises(InvalidEcalcModelException, match="same number of rate fractions"):
        PumpCommonStreamDistributionConfig(
            inlet_stream=liquid_stream_factory(),
            settings=[
                PumpCommonStreamSettings(rate_fractions=[expression_factory(1.0)], overflow=[]),
                PumpCommonStreamSettings(
                    rate_fractions=[expression_factory(0.5), expression_factory(0.5)], overflow=[]
                ),
            ],
        )


def test_individual_stream_distribution_requires_inlet_streams():
    with pytest.raises(InvalidEcalcModelException, match="at least one inlet stream"):
        _individual()


def test_pump_simulation_holds_process_configurations(liquid_stream_factory, pump_problem, expression_factory, periods):
    pressure_dropper_id = ProcessUnitId(uuid.uuid4())
    configuration = TimeSeriesPressureDropperConfiguration(pressure_drop_in_bara=expression_factory(4))

    simulation = PumpSimulation(
        name="a",
        stream_distribution=_individual(liquid_stream_factory()),
        pump_problems=_by_pipeline(pump_problem),
        process_periods=periods,
        process_configurations={pump_problem.get_pump_pipeline_id(): {pressure_dropper_id: configuration}},
    )

    assert simulation.get_process_configurations() == {
        pump_problem.get_pump_pipeline_id(): {pressure_dropper_id: configuration}
    }


def test_pump_simulation_rejects_process_configurations_for_other_pipeline(
    liquid_stream_factory, pump_problem, expression_factory, periods
):
    configuration = TimeSeriesPressureDropperConfiguration(pressure_drop_in_bara=expression_factory(4))

    with pytest.raises(InvalidEcalcModelException, match="which none of its pump problems simulate"):
        PumpSimulation(
            name="a",
            stream_distribution=_individual(liquid_stream_factory()),
            pump_problems=_by_pipeline(pump_problem),
            process_periods=periods,
            process_configurations={ProcessPipelineId(uuid.uuid4()): {ProcessUnitId(uuid.uuid4()): configuration}},
        )
