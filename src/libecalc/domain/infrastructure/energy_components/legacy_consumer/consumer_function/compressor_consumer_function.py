import numpy as np

from libecalc.common.fluid import FluidModel
from libecalc.common.utils.rates import Rates
from libecalc.common.variables import ExpressionEvaluator
from libecalc.domain.infrastructure.energy_components.legacy_consumer.consumer_function import (
    ConsumerFunction,
    ConsumerFunctionResult,
)
from libecalc.domain.infrastructure.energy_components.legacy_consumer.consumer_function.utils import (
    apply_condition,
    apply_power_loss_factor,
    get_condition_from_expression,
    get_power_loss_factor_from_expression,
)
from libecalc.domain.process.compressor.core.base import CompressorModel, CompressorWithTurbineModel
from libecalc.domain.process.compressor.core.train.variable_speed_compressor_train_common_shaft_multiple_streams_and_pressures import (
    VariableSpeedCompressorTrainCommonShaftMultipleStreamsAndPressures,
)
from libecalc.domain.process.core.results import CompressorTrainResult
from libecalc.expression import Expression


class CompressorConsumerFunction(ConsumerFunction):
    def __init__(
        self,
        compressor_function: CompressorModel,
        rate_expression: Expression | list[Expression],
        suction_pressure_expression: Expression,
        discharge_pressure_expression: Expression,
        condition_expression: Expression | None,
        power_loss_factor_expression: Expression | None,
        fluid_models: list[FluidModel] | None,
        intermediate_pressure_expression: Expression | None = None,
    ):
        """Note: If multiple streams and pressures, there will be  list of rate-Expressions, and there
            may be specification of intermediate pressure, stage number for intermediate pressure and specific
            pressure control mechanisms for first/last part of that compressor train. Except for that, all
            else is equal between the two compressor trans types.

        Initializes the CompressorConsumerFunction class, which defines the energy usage of a compressor.

        Args:
            compressor_function (CompressorModel): The compressor model to be used.
            rate_expression (Expression | list[Expression]): Rate expression(s) [Sm3/h].
                Can be a single expression or a list for multiple streams and pressures.
            suction_pressure_expression (Expression): Expression for suction pressure [bara].
            discharge_pressure_expression (Expression): Expression for discharge pressure [bara].
            fluid_models (list[FluidModel]): List of fluid models associated with the compressor.
            condition_expression (Expression | None): Optional condition expression to apply.
            power_loss_factor_expression (Expression | None): Optional expression for power loss factor,
                typically used for power line loss (e.g., subsea).
            intermediate_pressure_expression (Expression | None, optional): Expression for intermediate pressure,
                used in models with multiple streams and pressures. Defaults to None.
        """
        self._compressor_function = compressor_function
        self._rate_expression = rate_expression if isinstance(rate_expression, list) else [rate_expression]
        self._suction_pressure_expression = suction_pressure_expression
        self._discharge_pressure_expression = discharge_pressure_expression
        self._condition_expression = condition_expression
        self._power_loss_factor_expression = power_loss_factor_expression
        self._intermediate_pressure_expression = intermediate_pressure_expression
        self._fluid_models = fluid_models

    @property
    def suction_pressure(self) -> Expression:
        return self._suction_pressure_expression

    @property
    def discharge_pressure(self) -> Expression:
        return self._discharge_pressure_expression

    def evaluate(
        self,
        expression_evaluator: ExpressionEvaluator,
        regularity: list[float],
    ) -> ConsumerFunctionResult:
        """Evaluate the Compressor energy usage.
        :param expression_evaluator: Variables map is the VariablesMap-object holding all the data to be evaluated.
        :param regularity:
        :return:
        """
        calendar_day_rates = np.array(
            [expression_evaluator.evaluate(expression=rate_expression) for rate_expression in self._rate_expression]
        )
        # Squeeze to remove axes of length one -> non-multiple streams will be 1d and not 2d.
        # But we don't want to squeeze multiple streams model with only one date.
        # That goes for CompressorWithTurbineModel with a MultipleStreamsAndPressures-train as well
        if isinstance(self._compressor_function, CompressorWithTurbineModel):
            compressor_model = self._compressor_function.compressor_model
        else:
            compressor_model = self._compressor_function
        if isinstance(compressor_model, VariableSpeedCompressorTrainCommonShaftMultipleStreamsAndPressures):
            stream_day_rate = Rates.to_stream_day(
                calendar_day_rates=calendar_day_rates,
                regularity=regularity,
            )
        else:
            stream_day_rate = np.atleast_1d(
                np.squeeze(
                    Rates.to_stream_day(
                        calendar_day_rates=calendar_day_rates,
                        regularity=regularity,
                    )
                )
            )

        intermediate_pressure = (
            expression_evaluator.evaluate(expression=self._intermediate_pressure_expression)
            if self._intermediate_pressure_expression
            else None
        )
        suction_pressure = (
            expression_evaluator.evaluate(expression=self._suction_pressure_expression)
            if self._suction_pressure_expression is not None
            else None
        )
        discharge_pressure = (
            expression_evaluator.evaluate(expression=self._discharge_pressure_expression)
            if self._discharge_pressure_expression is not None
            else None
        )

        # Do conditioning first - set rates to zero if conditions are not met
        condition = get_condition_from_expression(
            expression_evaluator=expression_evaluator,
            condition_expression=self._condition_expression,
        )
        stream_day_rate_after_condition = apply_condition(
            input_array=stream_day_rate,
            condition=condition,  # type: ignore[arg-type]
        )

        # If the compressor model is supposed to have stages, make sure they are defined
        # (compressor sampled does not have stages)
        if isinstance(self._compressor_function, CompressorWithTurbineModel):
            self._compressor_function.compressor_model.check_for_undefined_stages(
                rate=stream_day_rate_after_condition,
                suction_pressure=suction_pressure,
                discharge_pressure=discharge_pressure,
            )
        else:
            self._compressor_function.check_for_undefined_stages(
                rate=stream_day_rate_after_condition,
                suction_pressure=suction_pressure,
                discharge_pressure=discharge_pressure,
            )

        compressor_train_result: CompressorTrainResult
        # Do not input regularity to compressor function. Handled outside
        # intermediate_pressure will only be different from None when we have a MultipleStreamsAndPressures train
        compressor_train_result = self._compressor_function.evaluate(
            rate=stream_day_rate_after_condition,
            suction_pressure=suction_pressure,
            discharge_pressure=discharge_pressure,
            intermediate_pressure=intermediate_pressure,
        )

        power_loss_factor = get_power_loss_factor_from_expression(
            expression_evaluator=expression_evaluator,
            power_loss_factor_expression=self._power_loss_factor_expression,
        )

        consumer_function_result = ConsumerFunctionResult(
            periods=expression_evaluator.get_periods(),
            is_valid=np.asarray(compressor_train_result.is_valid),
            energy_function_result=compressor_train_result,
            condition=condition,
            energy_usage_before_power_loss_factor=np.asarray(compressor_train_result.energy_usage),
            power_loss_factor=power_loss_factor,
            energy_usage=apply_power_loss_factor(
                energy_usage=np.asarray(compressor_train_result.energy_usage),
                power_loss_factor=power_loss_factor,
            ),
            power=apply_power_loss_factor(
                energy_usage=np.asarray(compressor_train_result.power),
                power_loss_factor=power_loss_factor,
            )
            if compressor_train_result.power is not None
            else None,
        )
        return consumer_function_result
