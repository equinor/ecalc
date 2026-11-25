from libecalc.ecalc_model.timeline_phase import TimelinePhase, TimelinePhaseType
from libecalc.expression.expression import Expression
from libecalc.presentation.yaml.domain.expression_timeline_phase_condition import ExpressionTimelinePhaseCondition
from libecalc.presentation.yaml.yaml_types.yaml_timeline import TimelinePhaseReference, YamlTimelinePhase


class TimelinePhaseMapper:
    def map_phases(self, yaml_timeline_phases: dict[TimelinePhaseReference, YamlTimelinePhase]) -> list[TimelinePhase]:
        return [
            TimelinePhase(
                reference=reference,
                title=yaml_phase.title or reference,
                type=TimelinePhaseType(yaml_phase.type.value),
                when=ExpressionTimelinePhaseCondition(Expression.setup_from_expression(yaml_phase.when)),
                description=yaml_phase.description,
            )
            for reference, yaml_phase in yaml_timeline_phases.items()
        ]
