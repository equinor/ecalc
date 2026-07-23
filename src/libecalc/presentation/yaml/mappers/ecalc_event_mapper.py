from libecalc.common.errors.ecalc_validation_error import EcalcValidationException
from libecalc.ecalc_model.ecalc_event import EcalcEvent, EcalcEventType, ProcessEvent, ProcessEventType
from libecalc.presentation.yaml.yaml_types.process.yaml_process_simulation import YamlEcalcEvent, YamlProcessEvent


class EcalcEventMapper:
    # TODO: Currently no services needed

    def map_events(
        self, yaml_ecalc_events: list[YamlEcalcEvent], yaml_process_events: list[YamlProcessEvent]
    ) -> list[EcalcEvent]:
        ecalc_events_by_name: dict[str, list[ProcessEvent]] = {}
        for yaml_event in yaml_ecalc_events:
            if yaml_event.name in ecalc_events_by_name:
                raise EcalcValidationException(
                    f"Duplicate ECALC_EVENT name '{yaml_event.name}'. Event names must be unique."
                )
            ecalc_events_by_name[yaml_event.name] = []

        for yaml_process_event in yaml_process_events:
            if yaml_process_event.ref not in ecalc_events_by_name:
                raise EcalcValidationException(
                    f"PROCESS_EVENT '{yaml_process_event.name}' references ECALC_EVENT '{yaml_process_event.ref}' which does not exist. "
                    f"Available: {', '.join(sorted(ecalc_events_by_name.keys()))}."
                )
            ecalc_events_by_name[yaml_process_event.ref].append(
                ProcessEvent(
                    name=yaml_process_event.name,
                    type=ProcessEventType(yaml_process_event.type.value),
                    description=yaml_process_event.description,
                )
            )

        ecalc_events: list[EcalcEvent] = []
        for yaml_event in yaml_ecalc_events:
            ecalc_events.append(
                EcalcEvent(
                    name=yaml_event.name,
                    type=EcalcEventType(yaml_event.type.value),
                    start=yaml_event.start,
                    description=yaml_event.description,
                    process_events=ecalc_events_by_name[yaml_event.name],
                )
            )

        return ecalc_events
