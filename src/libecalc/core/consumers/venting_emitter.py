from __future__ import annotations

from typing import Dict, List

from libecalc.common.logger import logger
from libecalc.common.temporal_model import TemporalExpression, TemporalModel
from libecalc.common.units import Unit
from libecalc.common.utils.rates import TimeSeriesStreamDayRate
from libecalc.core.result.emission import EmissionResult
from libecalc.dto.variables import VariablesMap
from libecalc.expression import Expression
from libecalc.presentation.yaml.yaml_types.emitters.yaml_venting_emitter import (
    YamlVentingEmitter,
)


class VentingEmitter:
    """A class for direct (not fuel based) emissions."""

    def __init__(self, to_core: YamlVentingEmitter):
        logger.debug(f"Creating VentingEmitter: {to_core.name}")

        self.to_core = to_core

    def evaluate(
        self,
        variables_map: VariablesMap,
    ) -> Dict[str, EmissionResult]:
        logger.debug(f"Evaluating VentingEmitter: {self.to_core.name}")

        emission_rate = self.evaluate_temporal(
            variables_map=variables_map,
            temporal_expression=self.to_core.temporal_emission_rate_model,
        )

        regularity = self.evaluate_temporal(
            variables_map=variables_map,
            temporal_expression=self.to_core.temporal_regularity_model,
        )

        emission_rate_stream_day = self.to_core.stream_day_rates(emission_rate, regularity, variables_map.time_vector)

        emission_name = self.to_core.emission_name
        emissions = {emission_name: EmissionResult.create_empty(name=emission_name, timesteps=[])}

        emission_rate_kg_per_day = emission_rate_stream_day
        emission_rate_tons_per_day = Unit.KILO_PER_DAY.to(Unit.TONS_PER_DAY)(emission_rate_kg_per_day)

        result = EmissionResult(
            name=emission_name,
            timesteps=variables_map.time_vector,
            rate=TimeSeriesStreamDayRate(
                timesteps=variables_map.time_vector,
                values=emission_rate_tons_per_day,
                unit=Unit.TONS_PER_DAY,
            ),
        )

        emissions[emission_name].extend(result)

        return dict(sorted(emissions.items()))

    @staticmethod
    def evaluate_temporal(variables_map: VariablesMap, temporal_expression: TemporalModel[Expression]) -> List[float]:
        return TemporalExpression.evaluate(
            temporal_expression=temporal_expression,
            variables_map=variables_map,
        )
