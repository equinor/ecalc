from typing import List, Literal

from pydantic import Field

from libecalc.expression.expression import ExpressionType
from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.components.legacy.energy_usage_model.common import (
    EnergyUsageModelCommon,
)


class YamlCompressorSystemCompressor(YamlBase):
    name: str = Field(
        ...,
        title="NAME",
        description="Name of the compressor",
    )
    compressor_model: str = Field(
        ...,
        title="COMPRESSOR_MODEL",
        description="Reference to a compressor type facility model defined in FACILITY_INPUTS",
    )


class YamlCompressorSystemOperationalSetting(YamlBase):
    crossover: List[int] = Field(
        None,
        title="CROSSOVER",
        description="Set cross over rules in system operational setting. \n\n$ECALC_DOCS_KEYWORDS_URL/OPERATIONAL_SETTINGS#crossover",
    )
    rates: List[ExpressionType] = Field(
        None,
        title="RATES",
        description="Set rate per consumer in a consumer system operational setting. \n\n$ECALC_DOCS_KEYWORDS_URL/OPERATIONAL_SETTINGS#rates",
    )
    rate_fractions: List[ExpressionType] = Field(
        None,
        title="RATE_FRACTIONS",
        description="List of expressions defining fractional rate (of total system rate) per consumer.  \n\n$ECALC_DOCS_KEYWORDS_URL/OPERATIONAL_SETTINGS#rate-fractions",
    )
    suction_pressures: List[ExpressionType] = Field(
        None,
        title="SUCTION_PRESSURES",
        description="Set suction pressure per consumer in a consumer system operational setting. \n\n$ECALC_DOCS_KEYWORDS_URL/OPERATIONAL_SETTINGS#suction-pressures",
    )
    discharge_pressures: List[ExpressionType] = Field(
        None,
        title="DISCHARGE_PRESSURES",
        description="Set discharge pressure per consumer in a consumer system operational setting. \n\n$ECALC_DOCS_KEYWORDS_URL/OPERATIONAL_SETTINGS#discharge-pressures",
    )
    discharge_pressure: ExpressionType = Field(
        None,
        title="DISCHARGE_PRESSURE",
        description="Set discharge pressure equal for all consumers in a consumer system operational setting. \n\n$ECALC_DOCS_KEYWORDS_URL/DISCHARGE_PRESSURE",
    )
    suction_pressure: ExpressionType = Field(
        None,
        title="SUCTION_PRESSURE",
        description="Set suction pressure equal for all consumers in a consumer system operational setting. \n\n$ECALC_DOCS_KEYWORDS_URL/SUCTION_PRESSURE",
    )


class YamlPumpSystemOperationalSettings(YamlCompressorSystemOperationalSetting):
    fluid_densities: List[ExpressionType] = Field(
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
    compressors: List[YamlCompressorSystemCompressor] = Field(
        ...,
        title="COMPRESSORS",
        description="The compressors in a compressor system. \n\n$ECALC_DOCS_KEYWORDS_URL/COMPRESSORS#compressors",
    )
    total_system_rate: ExpressionType = Field(
        None,
        title="TOTAL_SYSTEM_RATE",
        description="Total fluid rate through the system \n\n$ECALC_DOCS_KEYWORDS_URL/TOTAL_SYSTEM_RATE",
    )
    operational_settings: List[YamlCompressorSystemOperationalSetting] = Field(
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
    chart: str = Field(
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
    pumps: List[YamlPumpSystemPump] = Field(
        ...,
        title="PUMPS",
        description="The pumps in a pump system. \n\n$ECALC_DOCS_KEYWORDS_URL/PUMPS#pumps",
    )
    fluid_density: ExpressionType = Field(
        None,
        title="FLUID_DENSITY",
        description="Density of the fluid in kg/m3. \n\n$ECALC_DOCS_KEYWORDS_URL/FLUID_DENSITY",
    )
    total_system_rate: ExpressionType = Field(
        None,
        title="TOTAL_SYSTEM_RATE",
        description="Total fluid rate through the system \n\n$ECALC_DOCS_KEYWORDS_URL/TOTAL_SYSTEM_RATE",
    )
    operational_settings: List[YamlPumpSystemOperationalSettings] = Field(
        ...,
        title="OPERATIONAL_SETTINGS",
        description="Operational settings of the system. \n\n$ECALC_DOCS_KEYWORDS_URL/OPERATIONAL_SETTINGS",
    )
