from libecalc.common.temporal_model import TemporalModel
from libecalc.common.time_utils import Period
from libecalc.common.variables import ExpressionEvaluator
from libecalc.domain.infrastructure.emitters.fuel_consumer_emitter import EmissionFactors, EmissionName
from libecalc.expression import Expression
from libecalc.presentation.yaml.yaml_types.fuel_type.yaml_emission import YamlEmission
from libecalc.presentation.yaml.yaml_types.fuel_type.yaml_fuel_type import YamlFuelType


class TemporalEmissionFactors(EmissionFactors):
    def __init__(self, expression_evaluator: ExpressionEvaluator, temporal_fuel: TemporalModel[YamlFuelType]):
        self._expression_evaluator = expression_evaluator
        self._temporal_fuel = temporal_fuel

        emission_names = set()
        for model in temporal_fuel.get_models():
            for emission in model.emissions:
                emission_names.add(emission.name)
        self._emission_names = list(emission_names)

        self._expression_cache: dict[YamlEmission : list[float]] = {}

    def get_emissions(self) -> list[EmissionName]:
        return self._emission_names

    def get_emission_factor(self, emission_name: str, period: Period) -> float:
        model = self._temporal_fuel.get_model(period)

        for emission in model.emissions:
            if emission.name == emission_name:
                if emission not in self._expression_cache:
                    self._expression_cache[emission] = self._expression_evaluator.evaluate(
                        Expression.setup_from_expression(emission.factor)
                    )

                start_index, end_index = period.get_period_indices(self._expression_evaluator.get_periods())
                assert start_index + 1 == end_index, "Period should match a single index"
                return self._expression_cache[emission][start_index]

        # Default to 0 if model does not have emission specified
        return 0
