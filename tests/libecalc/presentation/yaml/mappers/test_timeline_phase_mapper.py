from libecalc.ecalc_model.timeline_phase import TimelinePhase, TimelinePhaseType
from libecalc.expression.expression import Expression
from libecalc.presentation.yaml.domain.expression_timeline_phase_condition import ExpressionTimelinePhaseCondition
from libecalc.presentation.yaml.mappers.timeline_phase_mapper import TimelinePhaseMapper
from libecalc.testing.process_builders import YamlTimelinePhaseBuilder


def test_maps_timeline_phase():
    yaml_phase = (
        YamlTimelinePhaseBuilder()
        .with_title("Rig campaign")
        .with_type(TimelinePhaseType.DRILLING)
        .with_when("SIM;DRILLING_FLAG")
        .validate()
    )

    assert TimelinePhaseMapper().map_phases({"rig_campaign": yaml_phase}) == [
        TimelinePhase(
            reference="rig_campaign",
            title="Rig campaign",
            type=TimelinePhaseType.DRILLING,
            when=ExpressionTimelinePhaseCondition(Expression.setup_from_expression("SIM;DRILLING_FLAG")),
            description=None,
        )
    ]


def test_title_defaults_to_reference():
    yaml_phase = YamlTimelinePhaseBuilder().with_type(TimelinePhaseType.PRODUCTION).with_when("1").validate()

    [phase] = TimelinePhaseMapper().map_phases({"production": yaml_phase})

    assert phase.title == "production"
