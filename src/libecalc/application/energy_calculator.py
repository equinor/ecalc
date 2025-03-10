import operator
from functools import reduce

from libecalc.common.math.numbers import Numbers
from libecalc.common.units import Unit
from libecalc.common.utils.rates import TimeSeriesFloat, TimeSeriesStreamDayRate
from libecalc.common.variables import ExpressionEvaluator
from libecalc.core.result import EcalcModelResult
from libecalc.core.result.emission import EmissionResult
from libecalc.domain.energy import ComponentEnergyContext, Emitter, EnergyModel


class Context(ComponentEnergyContext):
    def __init__(
        self,
        energy_model: EnergyModel,
        consumer_results: dict[str, EcalcModelResult],
        component_id: str,
    ):
        self._energy_model = energy_model
        self._consumer_results = consumer_results
        self._component_id = component_id

    def get_power_requirement(self) -> TimeSeriesFloat | None:
        consumer_power_usage = [
            self._consumer_results[consumer.id].component_result.power
            for consumer in self._energy_model.get_consumers(self._component_id)
            if self._consumer_results[consumer.id].component_result.power is not None
        ]

        if len(consumer_power_usage) < 1:
            return None

        if len(consumer_power_usage) == 1:
            return consumer_power_usage[0]

        return reduce(operator.add, consumer_power_usage)

    def get_fuel_usage(self) -> TimeSeriesStreamDayRate | None:
        energy_usage = self._consumer_results[self._component_id].component_result.energy_usage
        if energy_usage.unit == Unit.MEGA_WATT:
            # energy usage is power usage, not fuel usage.
            return None
        return energy_usage


class EnergyCalculator:
    def __init__(
        self,
        energy_model: EnergyModel,
        expression_evaluator: ExpressionEvaluator,
    ):
        self._energy_model = energy_model
        self._expression_evaluator = expression_evaluator
        self._consumer_results: dict[str, EcalcModelResult] = {}

    def _get_context(self, component_id: str) -> ComponentEnergyContext:
        return Context(
            energy_model=self._energy_model,
            consumer_results=self._consumer_results,
            component_id=component_id,
        )

    def evaluate_energy_usage(self) -> dict[str, EcalcModelResult]:
        energy_components = self._energy_model.get_energy_components()

        for energy_component in energy_components:
            if hasattr(energy_component, "evaluate_energy_usage"):
                context = self._get_context(energy_component.id)
                self._consumer_results.update(energy_component.evaluate_energy_usage(context=context))

        self._consumer_results = Numbers.format_results_to_precision(self._consumer_results, precision=6)
        return self._consumer_results

    def evaluate_emissions(self) -> dict[str, dict[str, EmissionResult]]:
        """
        Calculate emissions for fuel consumers and emitters

        Returns: a mapping from consumer_id to emissions
        """
        emission_results: dict[str, dict[str, EmissionResult]] = {}
        for energy_component in self._energy_model.get_energy_components():
            if isinstance(energy_component, Emitter):
                emission_result = energy_component.evaluate_emissions(
                    energy_context=self._get_context(energy_component.id),
                    energy_model=self._energy_model,
                )

                if emission_result is not None:
                    emission_results[energy_component.id] = emission_result

        return Numbers.format_results_to_precision(emission_results, precision=6)
