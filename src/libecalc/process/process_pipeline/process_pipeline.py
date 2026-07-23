import datetime
from collections.abc import Sequence
from enum import StrEnum
from typing import Final, NewType, Self
from uuid import UUID

from libecalc.common.ddd import value_object
from libecalc.common.ddd.entity import Entity
from libecalc.common.time_utils import Period
from libecalc.common.utils.ecalc_uuid import ecalc_id_generator
from libecalc.process.process_pipeline.process_unit import ProcessUnit, ProcessUnitId

ProcessPipelineId = NewType("ProcessPipelineId", UUID)
ProcessPipelineSectionId = NewType("ProcessPipelineSectionId", UUID)
ProcessUnitConnectionId = NewType("ProcessUnitConnectionId", UUID)


class PipelineEventAction(StrEnum):
    CHANGE = "CHANGE"
    ADD = "ADD"
    REMOVE = "REMOVE"


class PipelineEventChangeType(StrEnum):
    REBUNDLE = "REBUNDLE"


@value_object
class PipelineEvent:
    """Describes a change to a process unit in a pipeline, e.g. a compressor rebundle."""

    action: PipelineEventAction
    change_target: ProcessUnitId
    change_to: ProcessUnit  # Specification/definition
    change_type: PipelineEventChangeType
    change_time: datetime.datetime  # period only when evaluating "just before storing in db"
    # process_event_ref: str | None


class ProcessUnitConnection(Entity[ProcessUnitConnectionId]):
    def __init__(
        self,
        from_process_unit_id: ProcessUnitId,
        to_process_unit_id: ProcessUnitId,
        process_unit_connection_id: ProcessUnitConnectionId | None = None,
    ):
        self._from_process_unit_id = from_process_unit_id
        self._to_process_unit_id = to_process_unit_id
        self._id: Final[ProcessUnitConnectionId] = process_unit_connection_id or ProcessUnitConnection._create_id()

    def get_id(self) -> ProcessUnitConnectionId:
        return self._id

    def get_from_process_unit_id(self) -> ProcessUnitId:
        return self._from_process_unit_id

    def get_to_process_unit_id(self) -> ProcessUnitId:
        return self._to_process_unit_id

    @classmethod
    def _create_id(cls: type[Self]) -> ProcessUnitConnectionId:
        return ProcessUnitConnectionId(ecalc_id_generator())

    def __str__(self):
        return f"ProcessUnitConnection(process_unit_connection_id={self._id}, from_process_unit_id={self._from_process_unit_id}, to_process_unit_id={self._to_process_unit_id})"


class ProcessPipelineSection(Entity[ProcessPipelineSectionId]):
    def __init__(
        self,
        process_units: Sequence[ProcessUnit],  # TODO: Reassure they are in order
        process_pipeline_section_id: ProcessPipelineSectionId | None = None,
    ):
        self._process_units = process_units
        self._id: Final[ProcessPipelineSectionId] = process_pipeline_section_id or ProcessPipelineSection._create_id()

    def get_id(self) -> ProcessPipelineSectionId:
        return self._id

    def get_process_units(self) -> list[ProcessUnit]:
        return list(self._process_units)

    @classmethod
    def _create_id(cls: type[Self]) -> ProcessPipelineSectionId:
        return ProcessPipelineSectionId(ecalc_id_generator())

    def __str__(self):
        return f"ProcessPipelineSection(process_pipeline_section_id={self._id}, process_units={self._process_units})"


class ProcessPipeline(Entity[ProcessPipelineId]):
    """
    TODO: We define this class in process, but we do not use it here. We use it in the ephemeral mapping layer,
    when storing in db And some testing. We should move it.
    In particular because it creates the necessary connections, which means that they will get new IDs
    """

    def __init__(
        self,
        name: str,
        process_pipeline_sections: Sequence[ProcessPipelineSection],
        process_periods: list[Period],  # Sequential!
        process_pipeline_id: ProcessPipelineId | None = None,
        events: Sequence[PipelineEvent] | None = None,
    ):
        self._name = name
        self._process_pipeline_sections = process_pipeline_sections
        self._process_periods = process_periods
        self._events: Sequence[PipelineEvent] = events or []
        self._process_unit_connections = ProcessPipeline._create_process_unit_connections(  # NOTE: this can currently only be used in mapper, to create connections first time!
            process_pipeline_sections=process_pipeline_sections
        )
        self._process_pipeline_id = process_pipeline_id
        self._id: Final[ProcessPipelineId] = process_pipeline_id or ProcessPipeline._create_id()

    def get_id(self) -> ProcessPipelineId:
        return self._id

    def get_name(self) -> str:
        return self._name

    def get_process_pipeline_sections(self) -> Sequence[ProcessPipelineSection]:
        return self._process_pipeline_sections

    def get_process_unit_connections(self) -> Sequence[ProcessUnitConnection]:
        return self._process_unit_connections

    def get_process_units(self) -> Sequence[ProcessUnit]:
        return [
            process_unit
            for process_section in self.get_process_pipeline_sections()
            for process_unit in process_section.get_process_units()
        ]

    def get_events(self) -> Sequence[PipelineEvent]:
        return self._events

    def get_process_periods(self) -> list[Period]:
        return self._process_periods

    @classmethod
    def _create_id(cls: type[Self]) -> ProcessPipelineId:
        return ProcessPipelineId(ecalc_id_generator())

    @staticmethod
    def _create_process_unit_connections(
        process_pipeline_sections: Sequence[ProcessPipelineSection],
    ) -> Sequence[ProcessUnitConnection]:
        """
        Connections kept at this level for now. Could potentially be handled at section level, which makes more sense,
        if we define the owner of a connection to be the process unit with the OUTLET (the last process unit will then not
        own any connections, as it doesn't have an outlet ...). In this class we can therefore just gather/build connections
        from the process unit sections, either represented as connections or just "outlet"s, which is what we need to store
        stream info on. inlet is just the result from previous process unit or section or sth else. The parameter basically.

        Currently we keep it here though, because inlet and outlet are "equivalent", and we therefore have
        intra and inter connections between process units, ie. across sections. So, we need to make a decision on who,
        is the owner - the section or the pipeline. Since it is just an identifier based on the surrogate of from and to,
        with a unique id, with no extra information, we can generate it on the fly.

        Private, because this should be internal information handled by pipeline, and only exposed for read

        Args:
            process_pipeline_sections:

        Returns:

        """
        process_unit_connections: list[ProcessUnitConnection] = []

        previous_process_unit: ProcessUnit | None = None
        for process_section in process_pipeline_sections:  # Ordered, in sequence!
            for process_unit in process_section.get_process_units():  # Ordered, in sequence!
                if previous_process_unit is not None:
                    process_unit_connections.append(
                        ProcessUnitConnection(
                            from_process_unit_id=previous_process_unit.get_id(),
                            to_process_unit_id=process_unit.get_id(),
                        )
                    )

                previous_process_unit = process_unit

        return process_unit_connections

    def __str__(self):
        return f"ProcessPipeline(process_pipeline_id={self._id}, name={self._name}, process_pipeline_sections={self._process_pipeline_sections})"
