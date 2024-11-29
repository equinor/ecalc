from typing import Literal

from pydantic import Field, model_validator

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
    crossover: list[int] = Field(
        None,
        title="CROSSOVER",
        description="Set cross over rules in system operational setting. \n\n$ECALC_DOCS_KEYWORDS_URL/OPERATIONAL_SETTINGS#crossover",
    )
    rates: list[YamlExpressionType] = Field(
        None,
        title="RATES",
        description="Set rate per consumer in a consumer system operational setting. \n\n$ECALC_DOCS_KEYWORDS_URL/OPERATIONAL_SETTINGS#rates",
    )
    rate_fractions: list[YamlExpressionType] = Field(
        None,
        title="RATE_FRACTIONS",
        description="List of expressions defining fractional rate (of total system rate) per consumer.  \n\n$ECALC_DOCS_KEYWORDS_URL/OPERATIONAL_SETTINGS#rate-fractions",
    )
    suction_pressures: list[YamlExpressionType] = Field(
        None,
        title="SUCTION_PRESSURES",
        description="Set suction pressure per consumer in a consumer system operational setting. \n\n$ECALC_DOCS_KEYWORDS_URL/OPERATIONAL_SETTINGS#suction-pressures",
    )
    discharge_pressures: list[YamlExpressionType] = Field(
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

    @model_validator(mode="after")
    def ensure_increasing_cross_over(self):
        if self.crossover is None:
            return self
        for compressor_train_index, crossover_to in enumerate(self.crossover):
            crossover_to_compressor_train_index = (
                crossover_to - 1
            )  # compressor_train_index is 0-indexed, crossover_to is 1-indexed
            no_crossover = crossover_to == 0
            if crossover_to_compressor_train_index > compressor_train_index or no_crossover:
                pass  # passing excess rate to a comp. train not yet evaluated or no crossover defined for this comp. train
            else:
                raise ValueError(
                    f"Crossover: {self.crossover}\n"
                    "The compressor trains in the compressor system are not defined in the correct order, according to "
                    "the way the crossovers are set up. eCalc can now try to pass excess rates to compressor trains in "
                    "the system that has already been evaluated. \n\n"
                    "To avoid loops and to avoid passing rates to compressor trains that have already been "
                    "processed, the index of the crossovers should be either 0 (no crossover) or larger than the index "
                    "of the current compressor train (passing excess rate to a compressor train not yet evaluated). \n\n"
                    "CROSSOVER: [2, 3, 0] is valid, but CROSSOVER: [2, 1, 0] is not. \n"
                )

        return self

    def train_not_evaluated(self, index: int):
        if self.crossover is None:
            return False
        return self.crossover[index] == 0


class YamlPumpSystemOperationalSettings(YamlCompressorSystemOperationalSetting):
    fluid_densities: list[YamlExpressionType] = Field(
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
