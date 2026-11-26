from typing import Final, NewType, Self
from uuid import UUID

from libecalc.common.ddd.entity import Entity
from libecalc.common.utils.ecalc_uuid import ecalc_id_generator
from libecalc.ecalc_model.validation import InvalidEcalcModelException
from libecalc.process.process_pipeline.process_unit import ProcessUnitId

LiquidRecirculationLoopId = NewType("LiquidRecirculationLoopId", UUID)


class LiquidRecirculationLoop(Entity[LiquidRecirculationLoopId]):
    def __init__(
        self,
        mixer_process_unit_id: ProcessUnitId,
        splitter_process_unit_id: ProcessUnitId,
        liquid_recirculation_loop_id: LiquidRecirculationLoopId | None = None,
    ):
        if mixer_process_unit_id == splitter_process_unit_id:
            raise InvalidEcalcModelException(
                f"Liquid recirculation loop mixer and splitter must be different units, got '{mixer_process_unit_id}' "
                "for both."
            )
        self._mixer_process_unit_id: Final[ProcessUnitId] = mixer_process_unit_id
        self._splitter_process_unit_id: Final[ProcessUnitId] = splitter_process_unit_id
        self._id: Final[LiquidRecirculationLoopId] = (
            liquid_recirculation_loop_id or LiquidRecirculationLoop._create_id()
        )

    def get_id(self) -> LiquidRecirculationLoopId:
        return self._id

    @classmethod
    def _create_id(cls: type[Self]) -> LiquidRecirculationLoopId:
        return LiquidRecirculationLoopId(ecalc_id_generator())

    def get_mixer_process_unit_id(self) -> ProcessUnitId:
        return self._mixer_process_unit_id

    def get_splitter_process_unit_id(self) -> ProcessUnitId:
        return self._splitter_process_unit_id
