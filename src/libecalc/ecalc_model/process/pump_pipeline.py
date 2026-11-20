from collections.abc import Sequence
from itertools import pairwise
from typing import Final, Self

from libecalc.common.ddd.entity import Entity
from libecalc.common.time_utils import Period
from libecalc.common.utils.ecalc_uuid import ecalc_id_generator
from libecalc.ecalc_model.process.liquid_recirculation_loop import LiquidRecirculationLoop
from libecalc.ecalc_model.process.process_pipeline import ProcessUnitConnection
from libecalc.ecalc_model.process.process_units import (
    TimeSeriesDirectMixerProcessUnit,
    TimeSeriesDirectSplitterProcessUnit,
    TimeSeriesProcessUnit,
    TimeSeriesPumpProcessUnit,
)
from libecalc.ecalc_model.validation import (
    InvalidEcalcModelException,
    require_name,
    require_sequential_periods,
    require_unique,
)
from libecalc.process.process_pipeline.process_pipeline import ProcessPipelineId


class PumpPipeline(Entity[ProcessPipelineId]):
    def __init__(
        self,
        name: str,
        process_units: Sequence[TimeSeriesProcessUnit],
        process_periods: list[Period],
        process_pipeline_id: ProcessPipelineId | None = None,
        process_unit_connections: Sequence[ProcessUnitConnection] | None = None,
        recirculation_loops: Sequence[LiquidRecirculationLoop] | None = None,
    ):
        require_name(name, "Pump pipeline")
        subject = f"Pump pipeline '{name}'"
        require_sequential_periods(process_periods, subject)
        PumpPipeline._validate_process_units(process_units, subject)
        self._name = name
        self._process_periods = list(process_periods)
        self._process_units: Final[tuple[TimeSeriesProcessUnit, ...]] = tuple(process_units)
        self._process_unit_connections: Final[tuple[ProcessUnitConnection, ...]] = (
            PumpPipeline._validate_process_unit_connections(self._process_units, process_unit_connections)
            if process_unit_connections is not None
            else PumpPipeline._create_process_unit_connections(self._process_units)
        )
        self._recirculation_loops: Final[tuple[LiquidRecirculationLoop, ...]] = tuple(recirculation_loops or ())
        PumpPipeline._validate_recirculation_loops(self._process_units, self._recirculation_loops, subject)
        self._id: Final[ProcessPipelineId] = process_pipeline_id or PumpPipeline._create_id()

    @staticmethod
    def _validate_process_units(process_units: Sequence[TimeSeriesProcessUnit], subject: str) -> None:
        if not any(isinstance(process_unit, TimeSeriesPumpProcessUnit) for process_unit in process_units):
            raise InvalidEcalcModelException(f"{subject} must have at least one pump process unit.")
        require_unique((process_unit.get_id() for process_unit in process_units), f"{subject} process unit ids")

    @staticmethod
    def _validate_recirculation_loops(
        process_units: Sequence[TimeSeriesProcessUnit],
        recirculation_loops: Sequence[LiquidRecirculationLoop],
        subject: str,
    ) -> None:
        require_unique((loop.get_id() for loop in recirculation_loops), f"{subject} recirculation loop ids")
        index_by_id = {process_unit.get_id(): index for index, process_unit in enumerate(process_units)}
        for loop in recirculation_loops:
            mixer_index = index_by_id.get(loop.get_mixer_process_unit_id())
            splitter_index = index_by_id.get(loop.get_splitter_process_unit_id())
            if mixer_index is None or not isinstance(process_units[mixer_index], TimeSeriesDirectMixerProcessUnit):
                raise InvalidEcalcModelException(
                    f"{subject} recirculation loop mixer '{loop.get_mixer_process_unit_id()}' must be a direct mixer "
                    "in the pipeline."
                )
            if splitter_index is None or not isinstance(
                process_units[splitter_index], TimeSeriesDirectSplitterProcessUnit
            ):
                raise InvalidEcalcModelException(
                    f"{subject} recirculation loop splitter '{loop.get_splitter_process_unit_id()}' must be a direct "
                    "splitter in the pipeline."
                )
            if not mixer_index < splitter_index:
                raise InvalidEcalcModelException(
                    f"{subject} recirculation loop mixer must be upstream of its splitter."
                )

    @staticmethod
    def _create_process_unit_connections(
        process_units: Sequence[TimeSeriesProcessUnit],
    ) -> tuple[ProcessUnitConnection, ...]:
        return tuple(
            ProcessUnitConnection(
                from_process_unit_id=from_unit.get_id(),
                to_process_unit_id=to_unit.get_id(),
            )
            for from_unit, to_unit in pairwise(process_units)
        )

    @staticmethod
    def _validate_process_unit_connections(
        process_units: Sequence[TimeSeriesProcessUnit],
        process_unit_connections: Sequence[ProcessUnitConnection],
    ) -> tuple[ProcessUnitConnection, ...]:
        expected = [(from_unit.get_id(), to_unit.get_id()) for from_unit, to_unit in pairwise(process_units)]
        actual = [
            (connection.get_from_process_unit_id(), connection.get_to_process_unit_id())
            for connection in process_unit_connections
        ]
        if actual != expected:
            raise InvalidEcalcModelException("Pump pipeline connections must chain the process units in flow order.")
        require_unique((connection.get_id() for connection in process_unit_connections), "Pump pipeline connection ids")
        return tuple(process_unit_connections)

    def get_id(self) -> ProcessPipelineId:
        return self._id

    @classmethod
    def _create_id(cls: type[Self]) -> ProcessPipelineId:
        return ProcessPipelineId(ecalc_id_generator())

    def get_name(self) -> str:
        return self._name

    def get_process_periods(self) -> list[Period]:
        return self._process_periods

    def get_process_units(self) -> Sequence[TimeSeriesProcessUnit]:
        return self._process_units

    def get_process_unit_connections(self) -> Sequence[ProcessUnitConnection]:
        return self._process_unit_connections

    def get_recirculation_loops(self) -> Sequence[LiquidRecirculationLoop]:
        return self._recirculation_loops

    def __str__(self):
        return f"PumpPipeline(process_pipeline_id={self._id}, name={self._name}, process_units={self._process_units})"
