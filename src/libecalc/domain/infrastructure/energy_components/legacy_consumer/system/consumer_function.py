from abc import abstractmethod
from copy import deepcopy

import numpy as np
from numpy.typing import NDArray

from libecalc.common.errors.exceptions import IncompatibleDataError
from libecalc.common.list.list_utils import array_to_list
from libecalc.common.logger import logger
from libecalc.common.variables import ExpressionEvaluator
from libecalc.domain.infrastructure.energy_components.legacy_consumer.consumer_function import ConsumerFunction
from libecalc.domain.infrastructure.energy_components.legacy_consumer.consumer_function.utils import (
    apply_condition,
    apply_power_loss_factor,
    get_condition_from_expression,
    get_power_loss_factor_from_expression,
)
from libecalc.domain.infrastructure.energy_components.legacy_consumer.system.operational_setting import (
    CompressorSystemOperationalSetting,
    ConsumerSystemOperationalSetting,
    ConsumerSystemOperationalSettingExpressions,
    PumpSystemOperationalSetting,
)
from libecalc.domain.infrastructure.energy_components.legacy_consumer.system.results import (
    CompressorResult,
    ConsumerSystemComponentResult,
    ConsumerSystemConsumerFunctionResult,
    ConsumerSystemOperationalSettingResult,
    PumpResult,
)
from libecalc.domain.infrastructure.energy_components.legacy_consumer.system.types import ConsumerSystemComponent
from libecalc.domain.infrastructure.energy_components.legacy_consumer.system.utils import (
    assemble_operational_setting_from_model_result_list,
    get_operational_settings_number_used_from_model_results,
)
from libecalc.domain.process.compressor.core.base import CompressorModel, CompressorWithTurbineModel
from libecalc.domain.process.pump.pump import PumpModel
from libecalc.expression import Expression


class ConsumerSystemConsumerFunction(ConsumerFunction):
    def __init__(
        self,
        consumer_components: list[ConsumerSystemComponent],
        operational_settings_expressions: list[ConsumerSystemOperationalSettingExpressions],
        condition_expression: Expression | None,
        power_loss_factor_expression: Expression | None,
    ):
        """operational_settings_expressions, condition_expression and power_loss_factor_expression
        defines one expression per time-step.
        """
        self.consumers = consumer_components
        self.operational_settings_expressions = operational_settings_expressions
        self.condition_expression = condition_expression
        self.power_loss_factor_expression = power_loss_factor_expression

        for operational_settings_expression in operational_settings_expressions:
            if operational_settings_expression.number_of_consumers != len(consumer_components):
                message = (
                    f"Number of consumers in operational setting "
                    f"({operational_settings_expression.number_of_consumers})"
                    f" does not match the number of consumers in the consumer system ({len(consumer_components)})"
                )
                logger.error(message)
                raise IncompatibleDataError(message=message)

    @property
    def number_of_consumers(self) -> int:
        return len(self.consumers)

    @abstractmethod
    def evaluate_consumers(
        self,
        operational_setting: ConsumerSystemOperationalSetting,
    ) -> list[ConsumerSystemComponentResult]: ...

    @abstractmethod
    def evaluate_operational_setting_expressions(
        self,
        operational_setting_expressions: ConsumerSystemOperationalSettingExpressions,
        expression_evaluator: ExpressionEvaluator,
    ) -> ConsumerSystemOperationalSetting: ...

    def evaluate(
        self,
        expression_evaluator: ExpressionEvaluator,
        regularity: list[float],
    ) -> ConsumerSystemConsumerFunctionResult:
        """Steps in evaluating a consumer system:

        1. Convert operational settings from expressions to values
        2. Adjust operational settings for cross-overs (pre-processing)
        3. Evaluate condition from expressions to values
        4. Apply condition to operational settings
        5. Evaluate the consumer systems with the different operational settings
        6. Assemble the settings number used for each time step
        7. Assemble the operational setting based on 4.
        8. Evaluate of cross-over has been used.
        9. Run the consumers with the resulting Operational settings in 5.
        10. Compute the sum of energy and power used by the consumers
        11. Evaluate and apply power loss expressions
        12. Return a complete ConsumerSystemConsumerFunctionResult with data from the above steps.
        """
        operational_settings = self.get_operational_settings_from_expressions(
            expression_evaluator=expression_evaluator,
            regularity=regularity,
        )

        operational_settings_adjusted_for_cross_over = self.get_operational_settings_adjusted_for_cross_over(
            operational_settings=operational_settings
        )

        condition = get_condition_from_expression(
            expression_evaluator=expression_evaluator,
            condition_expression=self.condition_expression,
        )

        for operational_setting in operational_settings_adjusted_for_cross_over:
            operational_setting.__dict__["rates"] = [
                apply_condition(
                    input_array=rate,
                    condition=condition,
                )
                for rate in operational_setting.rates
            ]

        consumer_system_operational_settings_results = self.evaluate_system_operational_settings(
            operational_settings=operational_settings_adjusted_for_cross_over
        )

        operational_setting_number_used_per_timestep = get_operational_settings_number_used_from_model_results(
            consumer_system_operational_settings_results=consumer_system_operational_settings_results
        )

        operational_setting_used = assemble_operational_setting_from_model_result_list(
            operational_settings=operational_settings_adjusted_for_cross_over,
            setting_number_used_per_timestep=array_to_list(operational_setting_number_used_per_timestep),
        )
        operational_setting_used_without_cross_over = assemble_operational_setting_from_model_result_list(
            operational_settings=operational_settings,
            setting_number_used_per_timestep=array_to_list(operational_setting_number_used_per_timestep),
        )
        cross_over_used = self.get_cross_over_used(
            operational_setting_used_without_cross_over=operational_setting_used_without_cross_over,
            operational_settings_used=operational_setting_used,
        )

        consumer_results = self.evaluate_consumers(operational_setting=operational_setting_used)
        energy_usage = np.sum([np.asarray(result.energy_usage) for result in consumer_results], axis=0)
        power_usage = np.sum([np.asarray(result.power) for result in consumer_results], axis=0)

        power_loss_factor = get_power_loss_factor_from_expression(
            expression_evaluator=expression_evaluator,
            power_loss_factor_expression=self.power_loss_factor_expression,
        )

        return ConsumerSystemConsumerFunctionResult(
            periods=expression_evaluator.get_periods(),
            is_valid=np.multiply.reduce([x.consumer_model_result.is_valid for x in consumer_results]).astype(bool),
            operational_setting_used=operational_setting_number_used_per_timestep,
            operational_settings=[operational_settings],
            operational_settings_results=[consumer_system_operational_settings_results],
            consumer_results=[consumer_results],
            cross_over_used=cross_over_used,
            energy_usage_before_power_loss_factor=energy_usage,
            condition=condition,
            power_loss_factor=power_loss_factor,
            energy_usage=apply_power_loss_factor(
                energy_usage=energy_usage,
                power_loss_factor=power_loss_factor,
            ),
            power=apply_power_loss_factor(
                energy_usage=power_usage,
                power_loss_factor=power_loss_factor,
            ),
        )

    def get_operational_settings_from_expressions(
        self,
        expression_evaluator: ExpressionEvaluator,
        regularity: list[float],
    ) -> list[ConsumerSystemOperationalSetting]:
        """Evaluate operational settings expressions and return actual operational settings.

        If regularity is specified, interpret the rate in the operational setting
        as calendar day rate and compute the stream day rate. Return operational
        setting object where the rate is stream day

            rate_stream_day = rate_calendar_day / regularity

        regularity is between 0 and 1 (fraction of "full time")
        """
        # First evaluate operational settings expressions
        operational_settings_calendar_day = [
            self.evaluate_operational_setting_expressions(
                operational_setting_expressions=operational_setting,
                expression_evaluator=expression_evaluator,
            )
            for operational_setting in self.operational_settings_expressions
        ]

        # Convert rates to stream day rates
        operational_settings = [
            operational_setting.convert_rates_to_stream_day(regularity=regularity)
            for operational_setting in operational_settings_calendar_day
        ]

        return operational_settings

    def evaluate_system_operational_settings(
        self,
        operational_settings: list[ConsumerSystemOperationalSetting],
    ) -> list[ConsumerSystemOperationalSettingResult]:
        """Evaluate several operational settings. For details about evaluation of each operational setting,
        see description for method evaluate_operational_setting
        :type operational_settings:list[ConsumerSystemOperationalSetting]
        :rtype:list[ConsumerSystemOperationalSettingResult].
        """
        operational_settings_results = []
        for i, operational_setting in enumerate(operational_settings):
            logger.debug(f"Evaluating operational setting #{i}")
            operational_settings_results.append(
                ConsumerSystemOperationalSettingResult(
                    consumer_results=self.evaluate_consumers(operational_setting=operational_setting),
                )
            )
        return operational_settings_results

    def get_operational_settings_adjusted_for_cross_over(
        self, operational_settings: list[ConsumerSystemOperationalSetting]
    ) -> list[ConsumerSystemOperationalSetting]:
        operational_settings_after_cross_over = []
        for operational_setting in operational_settings:
            if operational_setting.cross_overs:
                operational_settings_after_cross_over.append(
                    self.calculate_operational_settings_after_cross_over(
                        operational_setting=operational_setting,
                    )
                )
            else:
                operational_settings_after_cross_over.append(operational_setting)
        return operational_settings_after_cross_over

    def calculate_operational_settings_after_cross_over(
        self,
        operational_setting: ConsumerSystemOperationalSetting,
    ) -> ConsumerSystemOperationalSetting:
        """Calculate rates after cross over is applied for consumers. Does not check if the
        "receiving" consumer now get a rate within it's capacity, just set rate of "sender"
        equal to it's maximum rate and add the rest to the "receiver".
        """
        cross_over_specification = operational_setting.cross_overs
        requested_rates = operational_setting.rates
        suction_pressures = operational_setting.suction_pressures
        discharge_pressures = operational_setting.discharge_pressures
        fluid_densities = operational_setting.fluid_densities

        rates_after_cross_over = deepcopy(requested_rates)
        for consumer_index, cross_over_number in enumerate(cross_over_specification):
            if cross_over_number == 0:
                continue
            consumer_suction_pressure = suction_pressures[consumer_index] if suction_pressures is not None else None
            consumer_discharge_pressure = (
                discharge_pressures[consumer_index] if discharge_pressures is not None else None
            )
            receiver_discharge_pressure = (
                discharge_pressures[cross_over_number - 1] if discharge_pressures is not None else None
            )
            energy_usage_model = self.consumers[consumer_index].facility_model

            if isinstance(energy_usage_model, CompressorModel):
                consumer_maximum_rate = energy_usage_model.get_max_standard_rate(
                    suction_pressures=consumer_suction_pressure,
                    discharge_pressures=consumer_discharge_pressure,
                )
            elif isinstance(energy_usage_model, PumpModel):
                consumer_fluid_density = fluid_densities[consumer_index] if fluid_densities is not None else None
                consumer_maximum_rate = energy_usage_model.get_max_standard_rate(
                    suction_pressures=consumer_suction_pressure,
                    discharge_pressures=consumer_discharge_pressure,
                    fluid_density=consumer_fluid_density,
                )
            else:
                raise NotImplementedError(
                    f"consumer system with energy usage model type:"
                    f" {type(energy_usage_model).__name__} has not been implemented."
                    f" This should not happen. Please contact eCalc support."
                )
            transfer_rate = requested_rates[consumer_index] - consumer_maximum_rate
            # Only transfer when max rate is exceeded
            transfer_rate = np.where(transfer_rate > 0, transfer_rate, 0)

            # Only transfer when the receiver discharge pressure >= sender discharge pressure
            transfer_rate = np.where(receiver_discharge_pressure >= consumer_discharge_pressure, transfer_rate, 0)

            # Subtract transfer rate on current consumer
            rates_after_cross_over[consumer_index] -= transfer_rate
            # Add transfer rate to receiving consumer
            rates_after_cross_over[cross_over_number - 1] += transfer_rate

        return operational_setting.model_copy(update={"rates": rates_after_cross_over})

    @staticmethod
    def get_cross_over_used(
        operational_setting_used_without_cross_over: ConsumerSystemOperationalSetting,
        operational_settings_used: ConsumerSystemOperationalSetting,
    ) -> NDArray[np.int_]:
        """Returns 1 for cross_over in use and 0 for not in use. One per timestep."""
        rates_before_cross_over = np.asarray(operational_setting_used_without_cross_over.rates)
        rates_adjusted_for_cross_over = np.asarray(operational_settings_used.rates)
        return np.array(
            np.any(np.where(rates_before_cross_over > rates_adjusted_for_cross_over, 1, 0), axis=0).astype(int)
        )


class CompressorSystemConsumerFunction(ConsumerSystemConsumerFunction):
    def evaluate_operational_setting_expressions(
        self,
        operational_setting_expressions: ConsumerSystemOperationalSettingExpressions,
        expression_evaluator: ExpressionEvaluator,
    ) -> ConsumerSystemOperationalSetting:
        """Evaluate all expressions in an operational setting with the input time series
        and time vector. Each expression evaluates to an array, and all arrays are
        returned in a data object with all arrays.

        Evaluate rate and pressure expressions in an OperationalSettingExpressions object
        """
        rates = [
            expression_evaluator.evaluate(rate_expression) for rate_expression in operational_setting_expressions.rates
        ]
        suction_pressures = [
            expression_evaluator.evaluate(suction_pressure_expression)
            for suction_pressure_expression in operational_setting_expressions.suction_pressures
        ]
        discharge_pressures = [
            expression_evaluator.evaluate(discharge_pressure_expression)
            for discharge_pressure_expression in operational_setting_expressions.discharge_pressures
        ]
        return CompressorSystemOperationalSetting(
            rates=rates,
            suction_pressures=suction_pressures,
            discharge_pressures=discharge_pressures,
            cross_overs=operational_setting_expressions.cross_overs,
        )

    def evaluate_consumers(
        self,
        operational_setting: ConsumerSystemOperationalSetting,
    ) -> list[CompressorResult]:
        """Evaluate a set of compressors in a consumer system for an operational setting
        which specifies variables for each compressor (rates, pressures).

        Return a list with results per compressor
        """
        consumer_rates = operational_setting.rates

        for i, consumer in enumerate(self.consumers):
            if isinstance(consumer.facility_model, CompressorWithTurbineModel):
                consumer.facility_model.compressor_model.check_for_undefined_stages(
                    rate=np.asarray(consumer_rates[i]),
                    suction_pressure=np.asarray(operational_setting.suction_pressures[i]),
                    discharge_pressure=np.asarray(operational_setting.discharge_pressures[i]),
                )
            else:
                consumer.facility_model.check_for_undefined_stages(
                    rate=np.asarray(consumer_rates[i]),
                    suction_pressure=np.asarray(operational_setting.suction_pressures[i]),
                    discharge_pressure=np.asarray(operational_setting.discharge_pressures[i]),
                )

        return [
            CompressorResult(
                name=consumer.name,
                consumer_model_result=consumer.facility_model.evaluate(
                    rate=consumer_rates[i],
                    suction_pressure=operational_setting.suction_pressures[i],
                    discharge_pressure=operational_setting.discharge_pressures[i],
                ),
            )
            for i, consumer in enumerate(self.consumers)
        ]


class PumpSystemConsumerFunction(ConsumerSystemConsumerFunction):
    def evaluate_operational_setting_expressions(
        self,
        operational_setting_expressions: ConsumerSystemOperationalSettingExpressions,
        expression_evaluator: ExpressionEvaluator,
    ) -> ConsumerSystemOperationalSetting:
        """Evaluate all expressions in an operational setting with the input time series
        and time vector. Each expression evaluates to an array, and all arrays are
        returned in a data object with all arrays.
        """
        rates = [
            expression_evaluator.evaluate(rate_expression) for rate_expression in operational_setting_expressions.rates
        ]
        suction_pressures = [
            expression_evaluator.evaluate(suction_pressure_expression)
            for suction_pressure_expression in operational_setting_expressions.suction_pressures
        ]
        discharge_pressures = [
            expression_evaluator.evaluate(discharge_pressure_expression)
            for discharge_pressure_expression in operational_setting_expressions.discharge_pressures
        ]
        fluid_densities = [
            expression_evaluator.evaluate(fluid_density_expression)
            for fluid_density_expression in operational_setting_expressions.fluid_densities
        ]
        return PumpSystemOperationalSetting(
            rates=rates,
            suction_pressures=suction_pressures,
            discharge_pressures=discharge_pressures,
            fluid_densities=fluid_densities,
            cross_overs=operational_setting_expressions.cross_overs,
        )

    def evaluate_consumers(
        self,
        operational_setting: ConsumerSystemOperationalSetting,
    ) -> list[PumpResult]:
        """Evaluate a set of pumps in a consumer system for an operational setting
        which specifies variables for each pump (rates, pressures, fluid densities).

        Return a list with results per pump
        """
        consumer_rates = operational_setting.rates
        consumer_suction_pressures = operational_setting.suction_pressures
        consumer_discharge_pressures = operational_setting.discharge_pressures
        consumer_fluid_densities = operational_setting.fluid_densities

        operational_setting_energy_usage_results = []
        for pump_number, pump in enumerate(self.consumers):
            logger.debug(f"Evaluating running pump#{pump_number} out of {self.number_of_consumers} pumps")

            pump_model_result = pump.facility_model.evaluate_rate_ps_pd_density(
                rate=np.asarray(consumer_rates[pump_number]),
                suction_pressures=np.asarray(consumer_suction_pressures[pump_number]),
                discharge_pressures=np.asarray(consumer_discharge_pressures[pump_number]),
                fluid_density=np.asarray(consumer_fluid_densities[pump_number]),
            )
            pump_result = PumpResult(
                name=pump.name,
                consumer_model_result=pump_model_result,
            )
            operational_setting_energy_usage_results.append(pump_result)
        return operational_setting_energy_usage_results
