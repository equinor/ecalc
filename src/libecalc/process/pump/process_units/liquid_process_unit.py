import abc
from typing import Self

from libecalc.common.ddd.entity import Entity
from libecalc.common.utils.ecalc_uuid import ecalc_id_generator
from libecalc.process.process_pipeline.process_unit import ProcessUnitId
from libecalc.process.pump.liquid_stream import LiquidStream


class LiquidProcessUnit(Entity[ProcessUnitId], abc.ABC):
    @abc.abstractmethod
    def get_id(self) -> ProcessUnitId: ...

    @abc.abstractmethod
    def propagate_stream(self, inlet_stream: LiquidStream) -> LiquidStream: ...

    @classmethod
    def _create_id(cls: type[Self]) -> ProcessUnitId:
        return ProcessUnitId(ecalc_id_generator())
