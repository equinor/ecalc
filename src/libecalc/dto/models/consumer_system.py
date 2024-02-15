from typing import List, Literal, Optional

from pydantic import Field, field_validator

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
from libecalc.dto.utils.validators import convert_expression, convert_expressions
from libecalc.expression import Expression


class CompressorSystemCompressor(EcalcBaseModel):
    name: str
    compressor_train: CompressorModel = Field(..., discriminator="typ")


class SystemOperationalSetting(EcalcBaseModel):
    rate_fractions: Optional[List[Expression]] = None
    rates: Optional[List[Expression]] = None
    suction_pressure: Optional[Expression] = None
    suction_pressures: Optional[List[Expression]] = None
    discharge_pressure: Optional[Expression] = None
    discharge_pressures: Optional[List[Expression]] = None
    crossover: Optional[List[int]] = None

    _convert_expression_lists = field_validator(
        "rate_fractions",
        "rates",
        "suction_pressures",
        "discharge_pressures",
        mode="before",
    )(convert_expressions)
    _convert_expression = field_validator("suction_pressure", "discharge_pressure", mode="before")(convert_expression)


class PumpSystemOperationalSetting(SystemOperationalSetting):
    fluid_densities: Optional[List[Expression]] = None

    _convert_expression_lists = field_validator(
        "fluid_densities",
        mode="before",
    )(convert_expressions)


class PumpSystemPump(EcalcBaseModel):
    name: str
    pump_model: PumpModel


class PumpSystemConsumerFunction(ConsumerFunction):
    typ: Literal[ConsumerType.PUMP_SYSTEM] = ConsumerType.PUMP_SYSTEM
    energy_usage_type: EnergyUsageType = EnergyUsageType.POWER
    power_loss_factor: Optional[Expression] = None
    pumps: List[PumpSystemPump]
    fluid_density: Expression
    total_system_rate: Optional[Expression] = None
    operational_settings: List[PumpSystemOperationalSetting]

    _convert_expression = field_validator("fluid_density", "total_system_rate", "power_loss_factor", mode="before")(
        convert_expression
    )


class CompressorSystemOperationalSetting(SystemOperationalSetting):
    pass


class CompressorSystemConsumerFunction(ConsumerFunction):
    typ: Literal[ConsumerType.COMPRESSOR_SYSTEM] = ConsumerType.COMPRESSOR_SYSTEM
    power_loss_factor: Optional[Expression] = None
    compressors: List[CompressorSystemCompressor]
    total_system_rate: Optional[Expression] = None
    operational_settings: List[CompressorSystemOperationalSetting]

    _convert_total_system_rate_to_expression = field_validator("total_system_rate", "power_loss_factor", mode="before")(
        convert_expression
    )

    @field_validator("compressors")
    @classmethod
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
