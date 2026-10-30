from libecalc.common.errors.ecalc_validation_error import EcalcValidationException
from libecalc.ecalc_model.ecalc_event import (
    EcalcEvent,
    EcalcEventType,
    EnergyEvent,
    EnergyEventType,
    ProcessEvent,
    ProcessEventType,
)
from libecalc.presentation.yaml.yaml_types.process.yaml_process_simulation import (
    YamlEcalcEvent,
    YamlEnergyEvent,
    YamlProcessEvent,
)


class EcalcEventMapper:
    # TODO: Currently no services needed

    def map_events(
        self,
        yaml_ecalc_events: list[YamlEcalcEvent],
        yaml_process_events: list[YamlProcessEvent],
        yaml_energy_events: list[YamlEnergyEvent],
    ) -> list[EcalcEvent]:
        process_events_by_ecalc_name: dict[str, list[ProcessEvent]] = {}
        energy_events_by_ecalc_name: dict[str, list[EnergyEvent]] = {}
        for yaml_event in yaml_ecalc_events:
            if yaml_event.name in process_events_by_ecalc_name:
                raise EcalcValidationException(
                    f"Duplicate ECALC_EVENT name '{yaml_event.name}'. Event names must be unique."
                )
            process_events_by_ecalc_name[yaml_event.name] = []
            energy_events_by_ecalc_name[yaml_event.name] = []

        for yaml_process_event in yaml_process_events:
            if yaml_process_event.ref not in process_events_by_ecalc_name:
                raise EcalcValidationException(
                    f"PROCESS_EVENT '{yaml_process_event.name}' references ECALC_EVENT '{yaml_process_event.ref}' which does not exist. "
                    f"Available: {', '.join(sorted(process_events_by_ecalc_name.keys()))}."
                )
            process_events_by_ecalc_name[yaml_process_event.ref].append(
                ProcessEvent(
                    name=yaml_process_event.name,
                    type=ProcessEventType(yaml_process_event.type.value),
                    description=yaml_process_event.description,
                )
            )

        for yaml_energy_event in yaml_energy_events:
            if yaml_energy_event.ref not in energy_events_by_ecalc_name:
                raise EcalcValidationException(
                    f"ENERGY_EVENT '{yaml_energy_event.name}' references ECALC_EVENT '{yaml_energy_event.ref}' which does not exist. "
                    f"Available: {', '.join(sorted(energy_events_by_ecalc_name.keys()))}."
                )
            energy_events_by_ecalc_name[yaml_energy_event.ref].append(
                EnergyEvent(
                    name=yaml_energy_event.name,
                    type=EnergyEventType(yaml_energy_event.type.value),
                    description=yaml_energy_event.description,
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
                    process_events=process_events_by_ecalc_name[yaml_event.name],
                    energy_events=energy_events_by_ecalc_name[yaml_event.name],
                )
            )

        return ecalc_events
