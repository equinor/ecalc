from typing import Literal

from libecalc.common.chart_type import ChartType
from libecalc.common.consumer_type import ConsumerType
from libecalc.common.energy_usage_type import EnergyUsageType
from libecalc.common.logger import logger
from libecalc.domain.process.compressor.dto.model_types import CompressorModelTypes
from libecalc.domain.process.compressor.dto.train import (
    CompressorTrainSimplifiedWithKnownStages,
    CompressorTrainSimplifiedWithUnknownStages,
)
from libecalc.domain.process.dto.base import ConsumerFunction
from libecalc.domain.process.pump.pump import PumpModelDTO
from libecalc.dto.utils.validators import convert_expression, convert_expressions
from libecalc.expression import Expression


class CompressorSystemCompressor:
    def __init__(self, name: str, compressor_train: CompressorModelTypes):
        self.name = name
        self.compressor_train = compressor_train


class SystemOperationalSetting:
    def __init__(
        self,
        rate_fractions: list[Expression] | None = None,
        rates: list[Expression] | None = None,
        suction_pressure: Expression | None = None,
        suction_pressures: list[Expression] | None = None,
        discharge_pressure: Expression | None = None,
        discharge_pressures: list[Expression] | None = None,
        crossover: list[int] | None = None,
    ):
        self.rate_fractions = convert_expressions(rate_fractions)
        self.rates = convert_expressions(rates)
        self.suction_pressure = convert_expression(suction_pressure)
        self.suction_pressures = convert_expressions(suction_pressures)
        self.discharge_pressure = convert_expression(discharge_pressure)
        self.discharge_pressures = convert_expressions(discharge_pressures)
        self.crossover = crossover


class PumpSystemOperationalSetting(SystemOperationalSetting):
    def __init__(
        self,
        rate_fractions: list[Expression] | None = None,
        rates: list[Expression] | None = None,
        suction_pressure: Expression | None = None,
        suction_pressures: list[Expression] | None = None,
        discharge_pressure: Expression | None = None,
        discharge_pressures: list[Expression] | None = None,
        crossover: list[int] | None = None,
        fluid_densities: list[Expression] | None = None,
    ):
        super().__init__(
            rate_fractions,
            rates,
            suction_pressure,
            suction_pressures,
            discharge_pressure,
            discharge_pressures,
            crossover,
        )
        self.fluid_densities = convert_expressions(fluid_densities)

    def __eq__(self, other):
        if not isinstance(other, PumpSystemOperationalSetting):
            return False
        return (
            self.rate_fractions == other.rate_fractions
            and self.rates == other.rates
            and self.suction_pressure == other.suction_pressure
            and self.suction_pressures == other.suction_pressures
            and self.discharge_pressure == other.discharge_pressure
            and self.discharge_pressures == other.discharge_pressures
            and self.crossover == other.crossover
            and self.fluid_densities == other.fluid_densities
        )


class PumpSystemPump:
    def __init__(self, name: str, pump_model: PumpModelDTO):
        self.name = name
        self.pump_model = pump_model

    def __eq__(self, other):
        if not isinstance(other, PumpSystemPump):
            return False
        return self.name == other.name and self.pump_model == other.pump_model


class PumpSystemConsumerFunction(ConsumerFunction):
    typ: Literal[ConsumerType.PUMP_SYSTEM] = ConsumerType.PUMP_SYSTEM
    energy_usage_type: EnergyUsageType = EnergyUsageType.POWER

    def __init__(
        self,
        condition: Expression | None = None,
        power_loss_factor: Expression | None = None,
        pumps: list[PumpSystemPump] = None,
        fluid_density: Expression = None,
        total_system_rate: Expression | None = None,
        operational_settings: list[PumpSystemOperationalSetting] = None,
    ):
        super().__init__(self.typ, self.energy_usage_type, condition)
        self.power_loss_factor = convert_expression(power_loss_factor)
        self.pumps = pumps
        self.fluid_density = convert_expression(fluid_density)
        self.total_system_rate = convert_expression(total_system_rate)
        self.operational_settings = operational_settings

    def __eq__(self, other):
        if not isinstance(other, PumpSystemConsumerFunction):
            return False
        return (
            self.typ == other.typ
            and self.energy_usage_type == other.energy_usage_type
            and self.power_loss_factor == other.power_loss_factor
            and self.condition == other.condition
            and self.pumps == other.pumps
            and self.fluid_density == other.fluid_density
            and self.total_system_rate == other.total_system_rate
            and self.operational_settings == other.operational_settings
        )


class CompressorSystemOperationalSetting(SystemOperationalSetting):
    def __init__(
        self,
        rate_fractions: list[Expression] | None = None,
        rates: list[Expression] | None = None,
        suction_pressure: Expression | None = None,
        suction_pressures: list[Expression] | None = None,
        discharge_pressure: Expression | None = None,
        discharge_pressures: list[Expression] | None = None,
        crossover: list[int] | None = None,
    ):
        super().__init__(
            rate_fractions,
            rates,
            suction_pressure,
            suction_pressures,
            discharge_pressure,
            discharge_pressures,
            crossover,
        )


class CompressorSystemConsumerFunction(ConsumerFunction):
    typ: Literal[ConsumerType.COMPRESSOR_SYSTEM] = ConsumerType.COMPRESSOR_SYSTEM

    def __init__(
        self,
        energy_usage_type: EnergyUsageType,
        condition: Expression | None = None,
        power_loss_factor: Expression | None = None,
        compressors: list[CompressorSystemCompressor] = None,
        total_system_rate: Expression | None = None,
        operational_settings: list[CompressorSystemOperationalSetting] = None,
    ):
        super().__init__(self.typ, energy_usage_type, condition)
        self.power_loss_factor = convert_expression(power_loss_factor)
        self.compressors = compressors
        self.total_system_rate = convert_expression(total_system_rate)
        self.operational_settings = operational_settings

    @staticmethod
    def check_for_generic_from_input_compressor_chart_in_simplified_train_compressor_system(
        compressors: list[CompressorSystemCompressor],
    ) -> list[CompressorSystemCompressor]:
        for compressor_system_compressor in compressors:
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
        return compressors
