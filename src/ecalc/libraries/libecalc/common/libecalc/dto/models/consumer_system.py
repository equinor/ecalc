from typing import List, Literal, Optional

from libecalc.common.logger import logger
from libecalc.dto.base import EcalcBaseModel
from libecalc.dto.models.base import ConsumerFunction
from libecalc.dto.models.compressor import CompressorModel
from libecalc.dto.models.compressor.train import (
    CompressorTrainSimplifiedWithKnownStages,
    CompressorTrainSimplifiedWithUnknownStages,
)
from libecalc.dto.models.pump import PumpModel
from libecalc.dto.types import ChartType, ConsumerType, EnergyUsageType
from libecalc.dto.utils.validators import convert_expression
from libecalc.expression import Expression
from pydantic import Field, validator


class CompressorSystemCompressor(EcalcBaseModel):
    name: str
    compressor_train: CompressorModel = Field(..., discriminator="typ")


class SystemOperationalSetting(EcalcBaseModel):
    rate_fractions: Optional[List[Expression]]
    rates: Optional[List[Expression]]
    suction_pressure: Optional[Expression]
    suction_pressures: Optional[List[Expression]]
    discharge_pressure: Optional[Expression]
    discharge_pressures: Optional[List[Expression]]
    crossover: Optional[List[int]]

    _convert_expression_lists = validator(
        "rate_fractions",
        "rates",
        "suction_pressures",
        "discharge_pressures",
        allow_reuse=True,
        pre=True,
        each_item=True,
    )(convert_expression)
    _convert_expression = validator("suction_pressure", "discharge_pressure", allow_reuse=True, pre=True)(
        convert_expression
    )


class PumpSystemOperationalSetting(SystemOperationalSetting):
    fluid_densities: Optional[List[Expression]]

    _convert_expression_lists = validator(
        "fluid_densities",
        allow_reuse=True,
        pre=True,
        each_item=True,
    )(convert_expression)


class PumpSystemPump(EcalcBaseModel):
    name: str
    pump_model: PumpModel


class PumpSystemConsumerFunction(ConsumerFunction):
    typ: Literal[ConsumerType.PUMP_SYSTEM] = ConsumerType.PUMP_SYSTEM
    energy_usage_type = EnergyUsageType.POWER
    power_loss_factor: Optional[Expression]
    pumps: List[PumpSystemPump]
    fluid_density: Expression
    total_system_rate: Optional[Expression]
    operational_settings: List[PumpSystemOperationalSetting]

    _convert_expression = validator(
        "fluid_density", "total_system_rate", "power_loss_factor", allow_reuse=True, pre=True
    )(convert_expression)


class CompressorSystemOperationalSetting(SystemOperationalSetting):
    pass


class CompressorSystemConsumerFunction(ConsumerFunction):
    typ: Literal[ConsumerType.COMPRESSOR_SYSTEM] = ConsumerType.COMPRESSOR_SYSTEM
    power_loss_factor: Optional[Expression]
    compressors: List[CompressorSystemCompressor]
    total_system_rate: Optional[Expression]
    operational_settings: List[CompressorSystemOperationalSetting]

    _convert_total_system_rate_to_expression = validator(
        "total_system_rate", "power_loss_factor", allow_reuse=True, pre=True
    )(convert_expression)

    @validator("compressors", pre=False)
    def check_for_generic_from_input_compressor_chart_in_simplified_train_compressor_system(
        cls, v: List[CompressorSystemCompressor]
    ) -> List[CompressorSystemCompressor]:
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
