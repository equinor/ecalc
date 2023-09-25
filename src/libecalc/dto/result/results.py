from __future__ import annotations

from operator import attrgetter
from typing import Any, Dict, List, Literal, Optional, Union

from libecalc.common.component_info.component_level import ComponentLevel
from libecalc.common.logger import logger
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
from libecalc.dto.result.simple import SimpleComponentResult, SimpleResultData
from libecalc.dto.result.tabular_time_series import TabularTimeSeries
from libecalc.dto.result.types import opt_float
from pydantic import Field, validator
from typing_extensions import Annotated


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

    def simple_result(self):
        return SimpleComponentResult(**self.dict())


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


class GeneratorSetResult(EquipmentResultBase):
    """The Generator set result component."""

    componentType: Literal[ComponentType.GENERATOR_SET]
    power_capacity_margin: TimeSeriesRate


class ConsumerSystemResult(EquipmentResultBase):
    componentType: Literal[
        ComponentType.PUMP_SYSTEM,
        ComponentType.COMPRESSOR_SYSTEM,
        ComponentType.COMPRESSOR_SYSTEM_V2,
        ComponentType.PUMP_SYSTEM_V2,
    ]

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


class CompressorResult(EquipmentResultBase):
    componentType: Literal[ComponentType.COMPRESSOR]
    recirculation_loss: TimeSeriesRate
    rate_exceeds_maximum: TimeSeriesBoolean
    outlet_pressure_before_choking: TimeSeriesFloat


class DirectEmitterResult(EquipmentResultBase):
    componentType: Literal[ComponentType.DIRECT_EMITTER]


class ConsumerModelResultBase(NodeInfo, CommonResultBase):
    """The Consumer base result component."""

    ...


class PumpModelResult(ConsumerModelResultBase):
    """The Pump result component."""

    componentType: Literal[ComponentType.PUMP]
    inlet_liquid_rate_m3_per_day: Optional[List[opt_float]]
    inlet_pressure_bar: Optional[List[opt_float]]
    outlet_pressure_bar: Optional[List[opt_float]]
    operational_head: Optional[List[float]]


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
        DirectEmitterResult,
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
    def components(self):
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

    def simple_result(self):
        return SimpleResultData(
            timesteps=self.timesteps, components=[component.simple_result() for component in self.components]
        )

    def resample(self, freq: Frequency) -> EcalcModelResult:
        return self.__class__(
            component_result=self.component_result.resample(freq),
            sub_components=[sub_component.resample(freq) for sub_component in self.sub_components],
            models=[model.resample(freq) for model in self.models],
        )
