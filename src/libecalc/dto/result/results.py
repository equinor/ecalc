from __future__ import annotations

from operator import attrgetter
from typing import Any, Dict, List, Literal, Optional, Union

try:
    from pydantic.v1 import Field, validator
except ImportError:
    from pydantic import Field, validator
from typing_extensions import Annotated

from libecalc.common.component_info.component_level import ComponentLevel
from libecalc.common.logger import logger
from libecalc.common.stream_conditions import TimeSeriesStreamConditions
from libecalc.common.time_utils import Frequency
from libecalc.common.units import Unit
from libecalc.common.utils.rates import (
    TimeSeriesBoolean,
    TimeSeriesFloat,
    TimeSeriesInt,
    TimeSeriesRate,
    TimeSeriesVolumesCumulative,
)
from libecalc.core.models.results.compressor import (
    CompressorTrainCommonShaftFailureStatus,
)
from libecalc.dto.base import ComponentType
from libecalc.dto.models import SingleSpeedChart, VariableSpeedChart
from libecalc.dto.result.base import EcalcResultBaseModel
from libecalc.dto.result.emission import EmissionIntensityResult, EmissionResult
from libecalc.dto.result.tabular_time_series import TabularTimeSeries


class NodeInfo(EcalcResultBaseModel):
    componentType: ComponentType
    component_level: ComponentLevel
    parent: Optional[str]  # reference parent id
    name: str


class CommonResultBase(TabularTimeSeries):
    """Base component for all results: Model, Installation, GenSet, Consumer System, Consumer, etc."""

    # we need to use camelCase here due to serialization/stub restrictions wrt FE stub generation

    is_valid: TimeSeriesBoolean

    # We need both energy usage and power rate since we sometimes want both fuel and power usage.
    energy_usage: TimeSeriesRate
    energy_usage_cumulative: TimeSeriesVolumesCumulative

    power: Optional[TimeSeriesRate] = None
    power_cumulative: Optional[TimeSeriesVolumesCumulative] = None


class ComponentResultBase(CommonResultBase, NodeInfo):
    id: str
    emissions: Dict[str, EmissionResult]


class EquipmentResultBase(ComponentResultBase):
    ...


class AssetResult(ComponentResultBase):
    """The aggregated eCalc model result."""

    componentType: Literal[ComponentType.ASSET]
    hydrocarbon_export_rate: TimeSeriesRate
    emission_intensities: List[EmissionIntensityResult]


class InstallationResult(AssetResult):
    """The installation result component."""

    componentType: Literal[ComponentType.INSTALLATION]
    regularity: TimeSeriesFloat  # Regularity is currently set at per installation, send through. Possibly skip in output if confusing


class GeneratorSetResult(EquipmentResultBase):
    """The Generator set result component."""

    componentType: Literal[ComponentType.GENERATOR_SET]
    power_capacity_margin: TimeSeriesRate


class ConsumerSystemResult(EquipmentResultBase):
    componentType: Literal[
        ComponentType.PUMP_SYSTEM,
        ComponentType.COMPRESSOR_SYSTEM,
        ComponentType.CONSUMER_SYSTEM_V2,
    ]

    consumer_type: Literal[ComponentType.COMPRESSOR, ComponentType.PUMP] = None

    @validator("consumer_type", pre=True)
    def set_consumer_type_based_on_component_type_if_possible(cls, consumer_type, values):
        """
        Set consumer type for legacy system where component type contains the same information.
        """
        component_type = values.get("componentType")
        if consumer_type is None:
            if component_type == ComponentType.PUMP_SYSTEM:
                return ComponentType.PUMP
            elif component_type == ComponentType.COMPRESSOR_SYSTEM:
                return ComponentType.COMPRESSOR

        return consumer_type

    operational_settings_used: Optional[TimeSeriesInt] = Field(
        None,
        description="The operational settings used for this system. "
        "0 indicates that no valid operational setting was found.",
    )
    operational_settings_results: Optional[Dict[int, List[Any]]]


class GenericConsumerResult(EquipmentResultBase):
    componentType: Literal[ComponentType.GENERIC]


class PumpResult(EquipmentResultBase):
    componentType: Literal[ComponentType.PUMP]
    inlet_liquid_rate_m3_per_day: TimeSeriesRate
    inlet_pressure_bar: TimeSeriesFloat
    outlet_pressure_bar: TimeSeriesFloat
    operational_head: TimeSeriesFloat

    streams: List[TimeSeriesStreamConditions] = None  # Optional because only in v2


class CompressorResult(EquipmentResultBase):
    componentType: Literal[ComponentType.COMPRESSOR]
    recirculation_loss: TimeSeriesRate
    rate_exceeds_maximum: TimeSeriesBoolean
    outlet_pressure_before_choking: TimeSeriesFloat

    streams: List[TimeSeriesStreamConditions] = None  # Optional because only in v2


class VentingEmitterResult(EquipmentResultBase):
    componentType: Literal[ComponentType.VENTING_EMITTER]


class ConsumerModelResultBase(NodeInfo, CommonResultBase):
    """The Consumer base result component."""

    ...


class PumpModelResult(ConsumerModelResultBase):
    """The Pump result component."""

    componentType: Literal[ComponentType.PUMP]
    inlet_liquid_rate_m3_per_day: Optional[TimeSeriesRate]
    inlet_pressure_bar: Optional[TimeSeriesFloat]
    outlet_pressure_bar: Optional[TimeSeriesFloat]
    operational_head: Optional[TimeSeriesFloat]
    is_valid: TimeSeriesBoolean


class TurbineModelResult(EcalcResultBaseModel):
    energy_usage_unit: Unit
    power_unit: Unit
    efficiency: TimeSeriesFloat
    energy_usage: TimeSeriesRate
    exceeds_maximum_load: TimeSeriesBoolean
    fuel_rate: TimeSeriesRate
    is_valid: TimeSeriesBoolean
    load: TimeSeriesRate
    power: TimeSeriesRate


class CompressorStreamConditionResult(EcalcResultBaseModel):
    actual_rate_m3_per_hr: TimeSeriesRate
    actual_rate_before_asv_m3_per_hr: TimeSeriesRate
    kappa: TimeSeriesFloat
    density_kg_per_m3: TimeSeriesRate
    pressure: TimeSeriesFloat
    pressure_before_choking: TimeSeriesFloat
    temperature_kelvin: TimeSeriesFloat
    z: TimeSeriesFloat


class CompressorModelStageResult(EcalcResultBaseModel):
    chart: Optional[Union[SingleSpeedChart, VariableSpeedChart]]
    chart_area_flags: List[str]
    energy_usage_unit: Unit
    power_unit: Unit
    fluid_composition: Dict[str, Optional[float]]

    head_exceeds_maximum: TimeSeriesBoolean
    is_valid: TimeSeriesBoolean
    polytropic_efficiency: TimeSeriesFloat
    polytropic_enthalpy_change_before_choke_kJ_per_kg: TimeSeriesFloat
    polytropic_enthalpy_change_kJ_per_kg: TimeSeriesFloat
    polytropic_head_kJ_per_kg: TimeSeriesFloat
    asv_recirculation_loss_mw: TimeSeriesRate
    energy_usage: TimeSeriesRate
    mass_rate_kg_per_hr: TimeSeriesRate
    mass_rate_before_asv_kg_per_hr: TimeSeriesRate
    power: TimeSeriesRate
    pressure_is_choked: TimeSeriesBoolean
    rate_exceeds_maximum: TimeSeriesBoolean
    rate_has_recirculation: TimeSeriesBoolean
    speed: TimeSeriesFloat
    inlet_stream_condition: CompressorStreamConditionResult
    outlet_stream_condition: CompressorStreamConditionResult


class CompressorModelResult(ConsumerModelResultBase):
    componentType: Literal[ComponentType.COMPRESSOR]
    failure_status: List[Optional[CompressorTrainCommonShaftFailureStatus]]
    requested_inlet_pressure: TimeSeriesFloat
    requested_outlet_pressure: TimeSeriesFloat
    rate: TimeSeriesRate
    maximum_rate: TimeSeriesRate
    stage_results: List[CompressorModelStageResult]
    turbine_result: Optional[TurbineModelResult] = None
    energy_usage_unit: Unit
    power_unit: Unit


class GenericModelResult(ConsumerModelResultBase):
    """Generic consumer result component."""

    componentType: Literal[ComponentType.GENERIC]


# Consumer result is referred to as ENERGY_USAGE_MODEL in the input YAML
ConsumerModelResult = Annotated[
    Union[CompressorModelResult, PumpModelResult, GenericModelResult],
    Field(discriminator="componentType"),
]

ComponentResult = Annotated[
    Union[
        AssetResult,
        InstallationResult,
        GeneratorSetResult,
        ConsumerSystemResult,
        CompressorResult,
        PumpResult,
        GenericConsumerResult,
        VentingEmitterResult,
    ],
    Field(discriminator="componentType"),
]


class EcalcModelResult(EcalcResultBaseModel):
    """Result object holding one component for each part of the eCalc model run:

    ModelResult, InstallationResult, GeneratorSetResult, ConsumerSystemResult, ConsumerGroupResult and ConsumerResult
    """

    component_result: ComponentResult
    # Setting min and max items to be able to generate OpenAPI:
    # Ref. https://github.com/developmentseed/geojson-pydantic/issues/42
    sub_components: Annotated[List[ComponentResult], Field(min_items=0, max_items=10000)]
    models: Annotated[List[ConsumerModelResult], Field(min_items=0, max_items=10000)]

    @validator("sub_components")
    def sort_sub_components(cls, sub_components):
        return sorted(sub_components, key=attrgetter("componentType", "name"))

    @validator("models")
    def sort_models(cls, models):
        return sorted(models, key=attrgetter("componentType", "name"))

    @property
    def timesteps(self):
        return self.component_result.timesteps

    @property
    def components(self) -> List[ComponentResult]:
        return [self.component_result, *self.sub_components]

    def get_components(self, component_ids: List[str]) -> List[ComponentResult]:
        return [component for component in self.components if component.id in component_ids]

    def get_component_by_name(self, component_name: str) -> Optional[ComponentResult]:
        components = [component for component in self.components if component.name == component_name]
        if not components:
            return None

        if len(components) > 1:
            logger.warning(f"Querying duplicate component {component_name}. Returning first match")

        return components[0]

    def resample(self, freq: Frequency) -> EcalcModelResult:
        return self.__class__(
            component_result=self.component_result.resample(freq),
            sub_components=[sub_component.resample(freq) for sub_component in self.sub_components],
            models=[model.resample(freq) for model in self.models],
        )
