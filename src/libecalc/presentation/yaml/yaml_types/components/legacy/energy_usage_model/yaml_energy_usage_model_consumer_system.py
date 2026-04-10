from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator
from pydantic_core.core_schema import ValidationInfo

from libecalc.presentation.yaml.yaml_keywords import EcalcYamlKeywords
from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.components.legacy.energy_usage_model.common import (
    EnergyUsageModelCommon,
)
from libecalc.presentation.yaml.yaml_types.components.yaml_expression_type import (
    YamlExpressionType,
)
from libecalc.presentation.yaml.yaml_types.models import YamlCompressorWithTurbine
from libecalc.presentation.yaml.yaml_types.models.model_reference_validation import (
    CompressorEnergyUsageModelModelReference,
    PumpEnergyUsageModelModelReference,
)
from libecalc.presentation.yaml.yaml_types.models.yaml_enums import YamlChartType


class YamlCompressorSystemCompressor(YamlBase):
    name: Annotated[
        str,
        Field(
            title="NAME",
            description="Name of the compressor",
        ),
    ]
    compressor_model: Annotated[
        CompressorEnergyUsageModelModelReference,
        Field(
            title="COMPRESSOR_MODEL",
            description="Reference to a compressor type facility model defined in FACILITY_INPUTS",
        ),
    ]


class YamlCompressorSystemOperationalSetting(YamlBase):
    crossover: Annotated[
        list[int] | None,
        Field(
            title="CROSSOVER",
            description="Set cross over rules in system operational setting. \n\n$ECALC_DOCS_KEYWORDS_URL/OPERATIONAL_SETTINGS#crossover",
        ),
    ] = None
    rates: Annotated[
        list[YamlExpressionType] | None,
        Field(
            title="RATES",
            description="Set rate per consumer in a consumer system operational setting. \n\n$ECALC_DOCS_KEYWORDS_URL/OPERATIONAL_SETTINGS#rates",
        ),
    ] = None
    rate_fractions: Annotated[
        list[YamlExpressionType] | None,
        Field(
            title="RATE_FRACTIONS",
            description="List of expressions defining fractional rate (of total system rate) per consumer.  \n\n$ECALC_DOCS_KEYWORDS_URL/OPERATIONAL_SETTINGS#rate-fractions",
        ),
    ] = None
    suction_pressures: Annotated[
        list[YamlExpressionType] | None,
        Field(
            title="SUCTION_PRESSURES",
            description="Set suction pressure per consumer in a consumer system operational setting. \n\n$ECALC_DOCS_KEYWORDS_URL/OPERATIONAL_SETTINGS#suction-pressures",
        ),
    ] = None
    discharge_pressures: Annotated[
        list[YamlExpressionType] | None,
        Field(
            title="DISCHARGE_PRESSURES",
            description="Set discharge pressure per consumer in a consumer system operational setting. \n\n$ECALC_DOCS_KEYWORDS_URL/OPERATIONAL_SETTINGS#discharge-pressures",
        ),
    ] = None
    discharge_pressure: Annotated[
        YamlExpressionType,
        Field(
            title="DISCHARGE_PRESSURE",
            description="Set discharge pressure equal for all consumers in a consumer system operational setting. \n\n$ECALC_DOCS_KEYWORDS_URL/DISCHARGE_PRESSURE",
        ),
    ] = None
    suction_pressure: Annotated[
        YamlExpressionType,
        Field(
            title="SUCTION_PRESSURE",
            description="Set suction pressure equal for all consumers in a consumer system operational setting. \n\n$ECALC_DOCS_KEYWORDS_URL/SUCTION_PRESSURE",
        ),
    ] = None


class YamlPumpSystemOperationalSettings(YamlCompressorSystemOperationalSetting):
    fluid_densities: Annotated[
        list[YamlExpressionType] | None,
        Field(
            title="FLUID_DENSITIES",
            description="Set fluid density per consumer in a consumer system operational setting. Will overwrite the systems common fluid density expression \n\n$ECALC_DOCS_KEYWORDS_URL/OPERATIONAL_SETTINGS#fluid-densities",
        ),
    ] = None


class YamlEnergyUsageModelCompressorSystem(EnergyUsageModelCommon):
    type: Annotated[
        Literal["COMPRESSOR_SYSTEM"],
        Field(
            title="TYPE",
            description="Defines the energy usage model type.\n\n$ECALC_DOCS_KEYWORDS_URL/TYPE",
        ),
    ]
    compressors: Annotated[
        list[YamlCompressorSystemCompressor],
        Field(
            title="COMPRESSORS",
            description="The compressors in a compressor system. \n\n$ECALC_DOCS_KEYWORDS_URL/COMPRESSORS#compressors",
        ),
    ]
    total_system_rate: Annotated[
        YamlExpressionType,
        Field(
            title="TOTAL_SYSTEM_RATE",
            description="Total fluid rate through the system \n\n$ECALC_DOCS_KEYWORDS_URL/TOTAL_SYSTEM_RATE",
        ),
    ] = None
    operational_settings: Annotated[
        list[YamlCompressorSystemOperationalSetting],
        Field(
            title="OPERATIONAL_SETTINGS",
            description="Operational settings of the system. \n\n$ECALC_DOCS_KEYWORDS_URL/OPERATIONAL_SETTINGS",
        ),
    ]

    @field_validator("compressors")
    def assert_unique_names(cls, compressors):
        unique_names = {compressor.name for compressor in compressors}
        if len(compressors) != len(unique_names):
            raise ValueError("Names must be unique within a compressor system")

        return compressors

    @model_validator(mode="after")
    def forbid_generic_from_input_and_unknown_stages_in_compressor_system(self, info: ValidationInfo):
        if not info.context:
            return self

        for compressor in self.compressors:
            compressor_model = info.context["model_types"][compressor.compressor_model]
            if isinstance(compressor_model, YamlCompressorWithTurbine):
                compressor_model = info.context["model_types"][compressor_model.compressor_model]
            train = getattr(compressor_model, "compressor_train", None)
            if not train:
                continue

            stages = getattr(train, EcalcYamlKeywords.models_type_compressor_train_stages.lower(), None)
            if stages:
                for stage in stages:
                    compressor_chart = info.context["model_types"].get(stage.compressor_chart)
                    if compressor_chart is None:
                        return self  # Handled in other validations, the compressor chart is invalid or non-existent
                    chart_type = getattr(compressor_chart, "chart_type", None)
                    if chart_type is None:
                        continue

                    if chart_type == YamlChartType.GENERIC_FROM_INPUT:
                        raise ValueError(
                            f"{chart_type.value} compressor chart is not supported for {self.type}. Chart reference: '{stage.compressor_chart}'"
                        )
            else:
                raise ValueError(f"A compressor train with unknown stages is not supported for {self.type}.")

        return self

    @model_validator(mode="after")
    def validate_operational_settings_match_compressors(self) -> "YamlEnergyUsageModelCompressorSystem":
        """Validate operational settings have consistent array lengths with number of compressors.

        Each operational setting must specify the same number of rates, suction pressures, and
        discharge pressures as there are compressors in the system.
        """
        num_compressors = len(self.compressors)

        for i, setting in enumerate(self.operational_settings):
            setting_num = i + 1  # 1-indexed for user-facing error messages

            # Validate rates (if using per-compressor rates)
            if setting.rates is not None:
                if len(setting.rates) != num_compressors:
                    raise ValueError(
                        f"Operational setting {setting_num}: RATES has {len(setting.rates)} values "
                        f"but system has {num_compressors} compressors. Each operational setting must "
                        f"specify rates for all compressors in the system."
                    )

            # Validate rate_fractions (if using fractions)
            if setting.rate_fractions is not None:
                if len(setting.rate_fractions) != num_compressors:
                    raise ValueError(
                        f"Operational setting {setting_num}: RATE_FRACTIONS has {len(setting.rate_fractions)} values "
                        f"but system has {num_compressors} compressors."
                    )

            # Validate suction_pressures (if using per-compressor pressures)
            if setting.suction_pressures is not None:
                if len(setting.suction_pressures) != num_compressors:
                    raise ValueError(
                        f"Operational setting {setting_num}: SUCTION_PRESSURES has {len(setting.suction_pressures)} values "
                        f"but system has {num_compressors} compressors."
                    )

            # Validate discharge_pressures (if using per-compressor pressures)
            if setting.discharge_pressures is not None:
                if len(setting.discharge_pressures) != num_compressors:
                    raise ValueError(
                        f"Operational setting {setting_num}: DISCHARGE_PRESSURES has {len(setting.discharge_pressures)} values "
                        f"but system has {num_compressors} compressors."
                    )

        return self


class YamlPumpSystemPump(YamlBase):
    name: Annotated[
        str,
        Field(
            title="NAME",
            description="Name of the pump",
        ),
    ]
    chart: Annotated[
        PumpEnergyUsageModelModelReference,
        Field(
            title="COMPRESSOR_MODEL",
            description="Reference to a pump type facility model defined in FACILITY_INPUTS",
        ),
    ]


class YamlEnergyUsageModelPumpSystem(EnergyUsageModelCommon):
    type: Annotated[
        Literal["PUMP_SYSTEM"],
        Field(
            title="TYPE",
            description="Defines the energy usage model type.\n\n$ECALC_DOCS_KEYWORDS_URL/TYPE",
        ),
    ]
    pumps: Annotated[
        list[YamlPumpSystemPump],
        Field(
            title="PUMPS",
            description="The pumps in a pump system. \n\n$ECALC_DOCS_KEYWORDS_URL/PUMPS#pumps",
        ),
    ]
    fluid_density: Annotated[
        YamlExpressionType,
        Field(
            title="FLUID_DENSITY",
            description="Density of the fluid in kg/m3. \n\n$ECALC_DOCS_KEYWORDS_URL/FLUID_DENSITY",
        ),
    ] = None
    total_system_rate: Annotated[
        YamlExpressionType,
        Field(
            title="TOTAL_SYSTEM_RATE",
            description="Total fluid rate through the system \n\n$ECALC_DOCS_KEYWORDS_URL/TOTAL_SYSTEM_RATE",
        ),
    ] = None
    operational_settings: Annotated[
        list[YamlPumpSystemOperationalSettings],
        Field(
            title="OPERATIONAL_SETTINGS",
            description="Operational settings of the system. \n\n$ECALC_DOCS_KEYWORDS_URL/OPERATIONAL_SETTINGS",
        ),
    ]

    @field_validator("pumps")
    def assert_unique_names(cls, pumps):
        unique_names = {pump.name for pump in pumps}
        if len(pumps) != len(unique_names):
            raise ValueError("Names must be unique within a pump system")

        return pumps

    @model_validator(mode="after")
    def validate_operational_settings_match_pumps(self) -> "YamlEnergyUsageModelPumpSystem":
        """Validate operational settings have consistent array lengths with number of pumps.

        Each operational setting must specify the same number of rates, suction pressures,
        discharge pressures, and fluid densities as there are pumps in the system.
        """
        num_pumps = len(self.pumps)

        for i, setting in enumerate(self.operational_settings):
            setting_num = i + 1  # 1-indexed for user-facing error messages

            # Validate rates (if using per-pump rates)
            if setting.rates is not None:
                if len(setting.rates) != num_pumps:
                    raise ValueError(
                        f"Operational setting {setting_num}: RATES has {len(setting.rates)} values "
                        f"but system has {num_pumps} pumps. Each operational setting must "
                        f"specify rates for all pumps in the system."
                    )

            # Validate rate_fractions (if using fractions)
            if setting.rate_fractions is not None:
                if len(setting.rate_fractions) != num_pumps:
                    raise ValueError(
                        f"Operational setting {setting_num}: RATE_FRACTIONS has {len(setting.rate_fractions)} values "
                        f"but system has {num_pumps} pumps."
                    )

            # Validate suction_pressures (if using per-pump pressures)
            if setting.suction_pressures is not None:
                if len(setting.suction_pressures) != num_pumps:
                    raise ValueError(
                        f"Operational setting {setting_num}: SUCTION_PRESSURES has {len(setting.suction_pressures)} values "
                        f"but system has {num_pumps} pumps."
                    )

            # Validate discharge_pressures (if using per-pump pressures)
            if setting.discharge_pressures is not None:
                if len(setting.discharge_pressures) != num_pumps:
                    raise ValueError(
                        f"Operational setting {setting_num}: DISCHARGE_PRESSURES has {len(setting.discharge_pressures)} values "
                        f"but system has {num_pumps} pumps."
                    )

            # Validate fluid_densities (pump-specific)
            if setting.fluid_densities is not None:
                if len(setting.fluid_densities) != num_pumps:
                    raise ValueError(
                        f"Operational setting {setting_num}: FLUID_DENSITIES has {len(setting.fluid_densities)} values "
                        f"but system has {num_pumps} pumps."
                    )

        return self
