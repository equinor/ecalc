from typing import Final, Self

from libecalc.common.ddd.entity import Entity
from libecalc.common.errors.exceptions import ProgrammingError
from libecalc.common.utils.ecalc_uuid import ecalc_id_generator
from libecalc.ecalc_model.equipment.equipment_id import EquipmentId
from libecalc.process.process_pipeline.process_unit import ProcessUnitId
from libecalc.process.process_solver.configuration import ConfigurationHandlerId


class TimeSeriesConfigurationHandlerBase(Entity[ConfigurationHandlerId]):
    def __init__(self, *, configuration_handler_id: ConfigurationHandlerId | None = None) -> None:
        self._id: Final[ConfigurationHandlerId] = configuration_handler_id or self._create_id()

    def get_id(self) -> ConfigurationHandlerId:
        return self._id

    @classmethod
    def _create_id(cls: type[Self]) -> ConfigurationHandlerId:
        return ConfigurationHandlerId(ecalc_id_generator())


class TimeSeriesShaftConfigurationHandler(TimeSeriesConfigurationHandlerBase):
    def __init__(
        self,
        *,
        shaft_equipment_id: EquipmentId,
        compressor_process_unit_ids: list[ProcessUnitId] | None = None,
        configuration_handler_id: ConfigurationHandlerId | None = None,
    ) -> None:
        super().__init__(configuration_handler_id=configuration_handler_id)
        self._shaft_equipment_id: Final[EquipmentId] = shaft_equipment_id
        self._compressor_process_unit_ids: list[ProcessUnitId] = list(compressor_process_unit_ids or [])

    @property
    def shaft_equipment_id(self) -> EquipmentId:
        return self._shaft_equipment_id

    def connect(self, compressor_process_unit_id: ProcessUnitId) -> None:
        if compressor_process_unit_id in self._compressor_process_unit_ids:
            raise ProgrammingError("Compressor is already registered on this shaft.")
        self._compressor_process_unit_ids.append(compressor_process_unit_id)

    def get_compressor_process_unit_ids(self) -> list[ProcessUnitId]:
        return list(self._compressor_process_unit_ids)


class TimeSeriesRecirculationLoopConfigurationHandler(TimeSeriesConfigurationHandlerBase):
    def __init__(
        self,
        *,
        mixer_process_unit_id: ProcessUnitId,
        splitter_process_unit_id: ProcessUnitId,
        configuration_handler_id: ConfigurationHandlerId | None = None,
    ) -> None:
        super().__init__(configuration_handler_id=configuration_handler_id)
        self._mixer_process_unit_id = mixer_process_unit_id
        self._splitter_process_unit_id = splitter_process_unit_id

    def get_mixer_process_unit_id(self) -> ProcessUnitId:
        return self._mixer_process_unit_id

    def get_splitter_process_unit_id(self) -> ProcessUnitId:
        return self._splitter_process_unit_id


class TimeSeriesChokeConfigurationHandler(TimeSeriesConfigurationHandlerBase):
    def __init__(
        self,
        *,
        choke_process_unit_id: ProcessUnitId,
        configuration_handler_id: ConfigurationHandlerId | None = None,
    ) -> None:
        super().__init__(configuration_handler_id=configuration_handler_id)
        self._choke_process_unit_id = choke_process_unit_id

    def get_choke_process_unit_id(self) -> ProcessUnitId:
        return self._choke_process_unit_id


type TimeSeriesConfigurationHandler = (
    TimeSeriesShaftConfigurationHandler
    | TimeSeriesRecirculationLoopConfigurationHandler
    | TimeSeriesChokeConfigurationHandler
)
