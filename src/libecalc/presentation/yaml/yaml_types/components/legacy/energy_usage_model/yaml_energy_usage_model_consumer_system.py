from typing import Literal

from pydantic import Field

from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.components.legacy.energy_usage_model.common import (
    EnergyUsageModelCommon,
)
from libecalc.presentation.yaml.yaml_types.components.yaml_expression_type import (
    YamlExpressionType,
)
from libecalc.presentation.yaml.yaml_types.models.model_reference_validation import (
    CompressorEnergyUsageModelModelReference,
    PumpEnergyUsageModelModelReference,
)


class YamlCompressorSystemCompressor(YamlBase):
    name: str = Field(
        ...,
        title="NAME",
        description="Name of the compressor",
    )
    compressor_model: CompressorEnergyUsageModelModelReference = Field(
        ...,
        title="COMPRESSOR_MODEL",
        description="Reference to a compressor type facility model defined in FACILITY_INPUTS",
    )


class YamlCompressorSystemOperationalSetting(YamlBase):
    crossover: list[int] | None = Field(
        None,
        title="CROSSOVER",
        description="Set cross over rules in system operational setting. \n\n$ECALC_DOCS_KEYWORDS_URL/OPERATIONAL_SETTINGS#crossover",
    )
    rates: list[YamlExpressionType] | None = Field(
        None,
        title="RATES",
        description="Set rate per consumer in a consumer system operational setting. \n\n$ECALC_DOCS_KEYWORDS_URL/OPERATIONAL_SETTINGS#rates",
    )
    rate_fractions: list[YamlExpressionType] | None = Field(
        None,
        title="RATE_FRACTIONS",
        description="List of expressions defining fractional rate (of total system rate) per consumer.  \n\n$ECALC_DOCS_KEYWORDS_URL/OPERATIONAL_SETTINGS#rate-fractions",
    )
    suction_pressures: list[YamlExpressionType] | None = Field(
        None,
        title="SUCTION_PRESSURES",
        description="Set suction pressure per consumer in a consumer system operational setting. \n\n$ECALC_DOCS_KEYWORDS_URL/OPERATIONAL_SETTINGS#suction-pressures",
    )
    discharge_pressures: list[YamlExpressionType] | None = Field(
        None,
        title="DISCHARGE_PRESSURES",
        description="Set discharge pressure per consumer in a consumer system operational setting. \n\n$ECALC_DOCS_KEYWORDS_URL/OPERATIONAL_SETTINGS#discharge-pressures",
    )
    discharge_pressure: YamlExpressionType = Field(
        None,
        title="DISCHARGE_PRESSURE",
        description="Set discharge pressure equal for all consumers in a consumer system operational setting. \n\n$ECALC_DOCS_KEYWORDS_URL/DISCHARGE_PRESSURE",
    )
    suction_pressure: YamlExpressionType = Field(
        None,
        title="SUCTION_PRESSURE",
        description="Set suction pressure equal for all consumers in a consumer system operational setting. \n\n$ECALC_DOCS_KEYWORDS_URL/SUCTION_PRESSURE",
    )


class YamlPumpSystemOperationalSettings(YamlCompressorSystemOperationalSetting):
    fluid_densities: list[YamlExpressionType] | None = Field(
        None,
        title="FLUID_DENSITIES",
        description="Set fluid density per consumer in a consumer system operational setting. Will overwrite the systems common fluid density expression \n\n$ECALC_DOCS_KEYWORDS_URL/OPERATIONAL_SETTINGS#fluid-densities",
    )


class YamlEnergyUsageModelCompressorSystem(EnergyUsageModelCommon):
    type: Literal["COMPRESSOR_SYSTEM"] = Field(
        ...,
        title="TYPE",
        description="Defines the energy usage model type.\n\n$ECALC_DOCS_KEYWORDS_URL/TYPE",
    )
    compressors: list[YamlCompressorSystemCompressor] = Field(
        ...,
        title="COMPRESSORS",
        description="The compressors in a compressor system. \n\n$ECALC_DOCS_KEYWORDS_URL/COMPRESSORS#compressors",
    )
    total_system_rate: YamlExpressionType = Field(
        None,
        title="TOTAL_SYSTEM_RATE",
        description="Total fluid rate through the system \n\n$ECALC_DOCS_KEYWORDS_URL/TOTAL_SYSTEM_RATE",
    )
    operational_settings: list[YamlCompressorSystemOperationalSetting] = Field(
        ...,
        title="OPERATIONAL_SETTINGS",
        description="Operational settings of the system. \n\n$ECALC_DOCS_KEYWORDS_URL/OPERATIONAL_SETTINGS",
    )


class YamlPumpSystemPump(YamlBase):
    name: str = Field(
        ...,
        title="NAME",
        description="Name of the pump",
    )
    chart: PumpEnergyUsageModelModelReference = Field(
        ...,
        title="COMPRESSOR_MODEL",
        description="Reference to a pump type facility model defined in FACILITY_INPUTS",
    )


class YamlEnergyUsageModelPumpSystem(EnergyUsageModelCommon):
    type: Literal["PUMP_SYSTEM"] = Field(
        ...,
        title="TYPE",
        description="Defines the energy usage model type.\n\n$ECALC_DOCS_KEYWORDS_URL/TYPE",
    )
    pumps: list[YamlPumpSystemPump] = Field(
        ...,
        title="PUMPS",
        description="The pumps in a pump system. \n\n$ECALC_DOCS_KEYWORDS_URL/PUMPS#pumps",
    )
    fluid_density: YamlExpressionType = Field(
        None,
        title="FLUID_DENSITY",
        description="Density of the fluid in kg/m3. \n\n$ECALC_DOCS_KEYWORDS_URL/FLUID_DENSITY",
    )
    total_system_rate: YamlExpressionType = Field(
        None,
        title="TOTAL_SYSTEM_RATE",
        description="Total fluid rate through the system \n\n$ECALC_DOCS_KEYWORDS_URL/TOTAL_SYSTEM_RATE",
    )
    operational_settings: list[YamlPumpSystemOperationalSettings] = Field(
        ...,
        title="OPERATIONAL_SETTINGS",
        description="Operational settings of the system. \n\n$ECALC_DOCS_KEYWORDS_URL/OPERATIONAL_SETTINGS",
    )
