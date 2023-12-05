from __future__ import annotations

from datetime import datetime
from typing import Dict, List

import numpy as np
from numpy.typing import NDArray

from libecalc import dto
from libecalc.common.logger import logger
from libecalc.common.temporal_model import TemporalExpression, TemporalModel
from libecalc.common.units import Unit
from libecalc.common.utils.rates import Rates, TimeSeriesStreamDayRate
from libecalc.core.result.emission import EmissionResult
from libecalc.dto.components import EmitterModel
from libecalc.dto.variables import VariablesMap
from libecalc.expression import Expression


class VentingEmitter:
    """A class for direct (not fuel based) emissions."""

    def __init__(self, venting_emitter_dto: dto.VentingEmitter):
        """We model a Venting Emitter as a Fuel Consumer, where the emission rate (kg/day) and
        the fuel rate (unit-less) are handled as 1 to 1.

        This means that we can simulate a direct emission as a normal fuel consumer the same,
        but using the simplification mentioned above.
        """
        logger.debug(f"Creating VentingEmitter: {venting_emitter_dto.name}")

        self.venting_emitter_dto = venting_emitter_dto

        self.temporal_emission_rate_model = TemporalModel(
            {
                start_time: emitter_model.emission_rate
                for start_time, emitter_model in venting_emitter_dto.emitter_model.items()
            }
        )

        self.temporal_regularity_model = TemporalModel(
            {
                regularity_time: regularity
                for model_time, emitter_model in venting_emitter_dto.emitter_model.items()
                for regularity_time, regularity in emitter_model.regularity.items()
            }
        )

    def evaluate(
        self,
        variables_map: VariablesMap,
    ) -> Dict[str, EmissionResult]:
        logger.debug(f"Evaluating VentingEmitter: {self.venting_emitter_dto.name}")
        emission_rate = self.evaluate_temporal(
            variables_map=variables_map, temporal_expression=self.temporal_emission_rate_model
        )
        regularity = self.evaluate_temporal(
            variables_map=variables_map, temporal_expression=self.temporal_regularity_model
        )

        emissions = self.evaluate_venting_emissions(
            variables_map=variables_map,
            emission_rate=np.asarray(emission_rate),
            emitter_model=self.venting_emitter_dto.emitter_model,
            regularity=np.asarray(regularity),
        )
        return emissions

    @staticmethod
    def evaluate_temporal(
        variables_map: dto.VariablesMap, temporal_expression: TemporalModel[Expression]
    ) -> List[float]:
        return TemporalExpression.evaluate(
            temporal_expression=temporal_expression,
            variables_map=variables_map,
        )

    def evaluate_venting_emissions(
        self,
        variables_map: dto.VariablesMap,
        emission_rate: NDArray[np.float64],
        regularity: NDArray[np.float64],
        emitter_model: Dict[datetime, EmitterModel],
    ) -> Dict[str, EmissionResult]:
        logger.debug("Evaluating fuel usage and emissions")

        # Creating a pseudo-default dict with all the emitters as keys. This is to handle changes in a temporal model.
        emission_name = self.venting_emitter_dto.emission_name
        emissions = {emission_name: EmissionResult.create_empty(name=emission_name, timesteps=[])}

        for period, model in TemporalModel(emitter_model).items():
            if model.convert_to_stream_day:
                start_index, end_index = period.get_timestep_indices(variables_map.time_vector)
                regularity_this_period = regularity[start_index:end_index]
                emission_rate[start_index:end_index] = Rates.to_stream_day(
                    emission_rate[start_index:end_index], regularity=list(regularity_this_period)
                )

        emission_rate_kg_per_day = emission_rate
        emission_rate_tons_per_day = Unit.KILO_PER_DAY.to(Unit.TONS_PER_DAY)(emission_rate_kg_per_day)

        result = EmissionResult(
            name=emission_name,
            timesteps=variables_map.time_vector,
            rate=TimeSeriesStreamDayRate(
                timesteps=variables_map.time_vector,
                values=emission_rate_tons_per_day.tolist(),
                unit=Unit.TONS_PER_DAY,
            ),
        )

        emissions[emission_name].extend(result)

        return dict(sorted(emissions.items()))
