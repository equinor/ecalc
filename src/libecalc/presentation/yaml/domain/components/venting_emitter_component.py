from datetime import datetime
from typing import Dict, Optional

import numpy as np

from libecalc.common.component_info.component_level import ComponentLevel
from libecalc.common.component_type import ComponentType
from libecalc.common.string.string_utils import generate_id
from libecalc.common.time_utils import Period
from libecalc.common.units import Unit
from libecalc.common.utils.rates import Rates, RateType, TimeSeriesFloat, TimeSeriesStreamDayRate
from libecalc.common.variables import ExpressionEvaluator
from libecalc.core.result import EcalcModelResult
from libecalc.core.result.emission import EmissionResult
from libecalc.dto.component_graph import Emitter
from libecalc.dto.node_info import NodeInfo
from libecalc.dto.utils.validators import convert_expression
from libecalc.expression import Expression
from libecalc.presentation.yaml.yaml_types.emitters.yaml_venting_emitter import YamlVentingEmitter


class VentingEmitter(Emitter):
    def __init__(
        self,
        yaml_venting_emitter: YamlVentingEmitter,
        regularity: Dict[datetime, Expression],
        expression_evaluator: ExpressionEvaluator,
    ):
        self._expression_evaluator = expression_evaluator
        self._yaml_venting_emitter = yaml_venting_emitter
        self._regularity = regularity

    @property
    def id(self):
        return generate_id(self._yaml_venting_emitter.name)

    def get_node_info(self) -> NodeInfo:
        return NodeInfo(
            id=self.id,
            name=self.name,
            component_level=ComponentLevel.CONSUMER,
            component_type=ComponentType.VENTING_EMITTER,
        )

    @property
    def name(self):
        return self._yaml_venting_emitter.name

    def get_emissions(self, period: Period = None) -> Dict[str, EmissionResult]:
        regularity_evaluated = self._expression_evaluator.evaluate(convert_expression(self._regularity)).tolist()
        oil_rates = self._expression_evaluator.evaluate(
            convert_expression(self._yaml_venting_emitter.volume.rate.value)
        ).tolist()

        if self._yaml_venting_emitter.volume.rate.type == RateType.CALENDAR_DAY:
            oil_rates = Rates.to_stream_day(
                calendar_day_rates=np.asarray(oil_rates),
                regularity=regularity_evaluated,
            ).tolist()

        emissions = {}
        for emission in self._yaml_venting_emitter.volume.emissions:
            factors = self._expression_evaluator.evaluate(convert_expression(emission.emission_factor))
            unit = self._yaml_venting_emitter.volume.rate.unit.to_unit()
            oil_rates = unit.to(Unit.STANDARD_CUBIC_METER_PER_DAY)(oil_rates)
            emission_rate = [oil_rate * factor for oil_rate, factor in zip(oil_rates, factors)]

            # Emission factor is kg/Sm3 and oil rate/volume is Sm3/d. Hence, the emission rate is in kg/d:
            emission_rate = Unit.KILO_PER_DAY.to(Unit.TONS_PER_DAY)(emission_rate)

            emissions[emission.name] = TimeSeriesStreamDayRate(
                timesteps=self._expression_evaluator.get_time_vector(),
                values=emission_rate,
                unit=Unit.TONS_PER_DAY,
            )
        venting_emitter_results = {}
        for emission_name, emission_rate in emissions.items():
            emission_result = EmissionResult(
                name=emission_name,
                timesteps=self._expression_evaluator.get_time_vector(),
                rate=emission_rate,
            )
            venting_emitter_results[emission_name] = emission_result
        return venting_emitter_results

    def get_oil_rates(
        self,
        expression_evaluator: ExpressionEvaluator,
        regularity: TimeSeriesFloat,
    ) -> TimeSeriesStreamDayRate:
        oil_rates = self._expression_evaluator.evaluate(
            convert_expression(self._yaml_venting_emitter.volume.rate.value)
        )

        if self._yaml_venting_emitter.volume.rate.type == RateType.CALENDAR_DAY:
            oil_rates = Rates.to_stream_day(
                calendar_day_rates=np.asarray(oil_rates),
                regularity=regularity.values,
            ).tolist()

        unit = self._yaml_venting_emitter.volume.rate.unit.to_unit()
        oil_rates = unit.to(Unit.STANDARD_CUBIC_METER_PER_DAY)(oil_rates)

        return TimeSeriesStreamDayRate(
            timesteps=expression_evaluator.get_time_vector(),
            values=oil_rates,
            unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
        )

    def get_ecalc_model_result(self) -> Optional[EcalcModelResult]:
        return None
