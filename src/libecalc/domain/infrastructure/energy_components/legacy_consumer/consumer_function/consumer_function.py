from __future__ import annotations

from abc import ABC, abstractmethod

from libecalc.common.variables import ExpressionEvaluator
from libecalc.domain.infrastructure.energy_components.legacy_consumer.consumer_function.results import (
    ConsumerFunctionResult,
)
from libecalc.expression import Expression


class ConsumerFunction(ABC):
    condition_expression: Expression
    power_loss_factor_expression: Expression

    @abstractmethod
    def evaluate(
        self,
        expression_evaluator: ExpressionEvaluator,
        regularity: list[float],
    ) -> ConsumerFunctionResult:
        """Referred to as ENERGY_USAGE_MODEL in yaml.

        Evaluation of a consumer function given a collection of time series cases
        In eCalc, consumer functions are functions defining a consumers energy usage [MW]
        A consumer function has an energy function which requires certain variables
        to be evaluated and expressions which defines these variables. When evaluating
        a consumer function the expressions are evaluated by the time series collection
        and the time vector and the result of these are used to evaluate the energy
        function to find the energy usage.

        If regularity is specified and is an array, this array must have the same length
        as the time_vector, i.e. the number of points to evaluate must be the same - and
        corresponding - in regularity. Thus each element in the regularity array correspond
        to the time step defined in time_vector at the same index

        Note: time_series have it's own time_vector - the total time_vector of the run.
        BUT - the time_vector here may be different from that, as it may be a subset for a
        specific time interval. time_series is where the vectors are retrieved/computed
        from and if the internal time vector if each reservoir input case does not coincide
        with the time_vector specified separately, these are interpolated (and possibly
        extrapolated) given the interpolation/extrapolation rules for that case.

        Example:
            A ConsumerFunction has
             - Model = f(x, y)
             - Expression_x = SIM1;GAS_PROD_A {+} 1
             - Expression_y = SIM2; GAS_PROD_B

            To evaluate
            1. calculate x from the time series collection, i.e. get the time series
             case SIM1 and from this retrieve the vector/time series GAS_PROD at the time steps
             defined in time_vector by using the interpolation type defined for this time
             series case. Finally add "1" as according to the expression. The result will
             thus be an array with the same length as time_vector.
            2. Calculate y in the same manner as x
            3. Evaluate the energy function, energy usage = f(x, y)
        """
        raise NotImplementedError
