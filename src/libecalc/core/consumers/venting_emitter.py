from __future__ import annotations

from typing import Dict, List

import numpy as np

from libecalc import dto
from libecalc.common.logger import logger
from libecalc.common.temporal_model import TemporalExpression, TemporalModel
from libecalc.core.models.fuel import FuelModel
from libecalc.core.result.emission import EmissionResult
from libecalc.dto import Emission
from libecalc.dto.types import FuelType
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
        self.temporal_fuel_model = FuelModel(
            {
                start_time: FuelType(
                    name=venting_emitter_dto.name,
                    # This is the VENTING-EMITTER CATEGORY which is fed into the fuel modet -> fuel validation error
                    # Commented out, meaning the fuel model has CATEGORY set to None
                    # user_defined_category=venting_emitter_dto.user_defined_category,
                    emissions=[
                        Emission(
                            name=venting_emitter_dto.emission_name,
                            factor=Expression.setup_from_expression(1),  # See docstring.  # See docstring
                        )
                    ],
                )
                for start_time, emitter_model in venting_emitter_dto.emitter_model.items()
            }
        )

        self.temporal_emission_rate_model = TemporalModel(
            {
                start_time: emitter_model.emission_rate
                for start_time, emitter_model in venting_emitter_dto.emitter_model.items()
            }
        )

    def evaluate(
        self,
        variables_map: VariablesMap,
    ) -> Dict[str, EmissionResult]:
        logger.debug(f"Evaluating VentingEmitter: {self.venting_emitter_dto.name}")
        fuel_rate = self.evaluate_fuel_rate(variables_map=variables_map)
        return self.temporal_fuel_model.evaluate_emissions(
            variables_map=variables_map,
            fuel_rate=np.asarray(fuel_rate),
        )

    def evaluate_fuel_rate(self, variables_map: dto.VariablesMap) -> List[float]:
        """We model fuel [unit-less] and emission rate [kg/day] as 1 to 1, thus we return the emission rate as
        a proxy for fuel rate.

        See the main docstring of this class.
        """
        return TemporalExpression.evaluate(
            temporal_expression=self.temporal_emission_rate_model,
            variables_map=variables_map,
        )