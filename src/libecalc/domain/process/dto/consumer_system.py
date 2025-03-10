from typing import Literal

from pydantic import Field, field_validator

from libecalc.common.chart_type import ChartType
from libecalc.common.consumer_type import ConsumerType
from libecalc.common.energy_usage_type import EnergyUsageType
from libecalc.common.logger import logger
from libecalc.domain.process.dto.base import ConsumerFunction
from libecalc.domain.process.dto.compressor import CompressorModel
from libecalc.domain.process.dto.compressor.train import (
    CompressorTrainSimplifiedWithKnownStages,
    CompressorTrainSimplifiedWithUnknownStages,
)
from libecalc.domain.process.pump.pump import PumpModelDTO
from libecalc.dto.base import EcalcBaseModel
from libecalc.dto.utils.validators import convert_expression, convert_expressions
from libecalc.expression import Expression


class CompressorSystemCompressor(EcalcBaseModel):
    name: str
    compressor_train: CompressorModel = Field(..., discriminator="typ")


class SystemOperationalSetting(EcalcBaseModel):
    rate_fractions: list[Expression] | None = None
    rates: list[Expression] | None = None
    suction_pressure: Expression | None = None
    suction_pressures: list[Expression] | None = None
    discharge_pressure: Expression | None = None
    discharge_pressures: list[Expression] | None = None
    crossover: list[int] | None = None

    _convert_expression_lists = field_validator(
        "rate_fractions",
        "rates",
        "suction_pressures",
        "discharge_pressures",
        mode="before",
    )(convert_expressions)
    _convert_expression = field_validator("suction_pressure", "discharge_pressure", mode="before")(convert_expression)


class PumpSystemOperationalSetting(SystemOperationalSetting):
    fluid_densities: list[Expression] | None = None

    _convert_expression_lists = field_validator(
        "fluid_densities",
        mode="before",
    )(convert_expressions)


class PumpSystemPump(EcalcBaseModel):
    name: str
    pump_model: PumpModelDTO


class PumpSystemConsumerFunction(ConsumerFunction):
    typ: Literal[ConsumerType.PUMP_SYSTEM] = ConsumerType.PUMP_SYSTEM
    energy_usage_type: EnergyUsageType = EnergyUsageType.POWER
    power_loss_factor: Expression | None = None
    pumps: list[PumpSystemPump]
    fluid_density: Expression
    total_system_rate: Expression | None = None
    operational_settings: list[PumpSystemOperationalSetting]

    _convert_expression = field_validator("fluid_density", "total_system_rate", "power_loss_factor", mode="before")(
        convert_expression
    )


class CompressorSystemOperationalSetting(SystemOperationalSetting):
    pass


class CompressorSystemConsumerFunction(ConsumerFunction):
    typ: Literal[ConsumerType.COMPRESSOR_SYSTEM] = ConsumerType.COMPRESSOR_SYSTEM
    power_loss_factor: Expression | None = None
    compressors: list[CompressorSystemCompressor]
    total_system_rate: Expression | None = None
    operational_settings: list[CompressorSystemOperationalSetting]

    _convert_total_system_rate_to_expression = field_validator("total_system_rate", "power_loss_factor", mode="before")(
        convert_expression
    )

    @field_validator("compressors")
    @classmethod
    def check_for_generic_from_input_compressor_chart_in_simplified_train_compressor_system(
        cls, v: list[CompressorSystemCompressor]
    ) -> list[CompressorSystemCompressor]:
        for compressor_system_compressor in v:
            compressor_train = compressor_system_compressor.compressor_train
            if isinstance(compressor_train, CompressorTrainSimplifiedWithKnownStages):
                for i, stage in enumerate(compressor_train.stages):
                    if stage.compressor_chart.typ == ChartType.GENERIC_FROM_INPUT:
                        logger.warning(
                            f"Stage number {i + 1} in {compressor_system_compressor.name} uses GENERIC_FROM_INPUT. "
                            f"Beware that when splitting rates on several compressor trains in a compressor system, "
                            f"the rate input used to generate a specific compressor chart will also change. Consider"
                            f" to define a design point yourself instead of letting an algorithm find one based on"
                            f" changing rates!"
                        )
            elif isinstance(compressor_train, CompressorTrainSimplifiedWithUnknownStages):
                if compressor_train.stage.compressor_chart.typ == ChartType.GENERIC_FROM_INPUT:
                    logger.warning(
                        f"Compressor chart in {compressor_system_compressor.name} uses GENERIC_FROM_INPUT. "
                        f"Beware that when splitting rates on several compressor trains in a compressor system, "
                        f"the rate input used to generate a specific compressor chart will also change. Consider"
                        f" to define a design point yourself instead of letting an algorithm find one based on"
                        f" changing rates!"
                    )
        return v
