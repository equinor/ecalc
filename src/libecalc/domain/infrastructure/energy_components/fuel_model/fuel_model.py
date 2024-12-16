from abc import ABC, abstractmethod
from collections import defaultdict
from datetime import datetime
from typing import Annotated, Any, Literal, Optional, TypeVar, Union, overload

import numpy as np
from pydantic import ConfigDict, Field, field_validator, model_validator
from pydantic_core.core_schema import ValidationInfo

from libecalc.application.energy.component_energy_context import ComponentEnergyContext
from libecalc.application.energy.emitter import Emitter
from libecalc.application.energy.energy_component import EnergyComponent
from libecalc.application.energy.energy_model import EnergyModel
from libecalc.common.component_type import ComponentType
from libecalc.common.consumption_type import ConsumptionType
from libecalc.common.energy_usage_type import EnergyUsageType
from libecalc.common.logger import logger
from libecalc.common.priorities import Priorities
from libecalc.common.priority_optimizer import PriorityOptimizer
from libecalc.common.stream_conditions import TimeSeriesStreamConditions
from libecalc.common.string.string_utils import generate_id
from libecalc.common.temporal_model import TemporalModel
from libecalc.common.time_utils import Period, Periods
from libecalc.common.units import Unit
from libecalc.common.utils.rates import (
    RateType,
    TimeSeriesFloat,
    TimeSeriesInt,
    TimeSeriesStreamDayRate,
    TimeSeriesString,
)
from libecalc.common.variables import ExpressionEvaluator
from libecalc.core.models.compressor import create_compressor_model
from libecalc.core.models.generator import GeneratorModelSampled
from libecalc.core.models.pump import create_pump_model
from libecalc.core.result import ComponentResult, EcalcModelResult
from libecalc.core.result.emission import EmissionResult
from libecalc.domain.infrastructure.energy_components.compressor import Compressor
from libecalc.domain.infrastructure.energy_components.consumer_system.consumer_system import (
    ConsumerSystem as ConsumerSystemEnergyComponent,
)
from libecalc.domain.infrastructure.energy_components.fuel_consumer.fuel_consumer import FuelConsumer
from libecalc.domain.infrastructure.energy_components.generator_set.generator_set import Genset
from libecalc.domain.infrastructure.energy_components.pump import Pump
from libecalc.dto.base import (
    EcalcBaseModel,
)
from libecalc.dto.component_graph import ComponentGraph
from libecalc.dto.fuel_type import FuelType
from libecalc.dto.models import (
    ConsumerFunction,
    GeneratorSetSampled,
)
from libecalc.dto.models.compressor import CompressorModel
from libecalc.dto.models.pump import PumpModel
from libecalc.dto.types import ConsumerUserDefinedCategoryType, InstallationUserDefinedCategoryType
from libecalc.dto.utils.validators import (
    ComponentNameStr,
    ExpressionType,
    convert_expression,
    validate_temporal_model,
)
from libecalc.expression import Expression
from libecalc.presentation.yaml.ltp_validation import (
    validate_generator_set_power_from_shore,
)
from libecalc.presentation.yaml.yaml_keywords import EcalcYamlKeywords
from libecalc.presentation.yaml.yaml_types.emitters.yaml_venting_emitter import (
    YamlVentingEmitter,
)


class FuelModel:
    """A function to evaluate fuel related attributes for different time period
    For each period, there is a data object with expressions for fuel related
    attributes which may be evaluated for some variables and a fuel_rate.
    """

    def __init__(self, fuel_time_function_dict: dict[Period, FuelType]):
        logger.debug("Creating fuel model")
        self.temporal_fuel_model = fuel_time_function_dict

    def evaluate_emissions(
        self, expression_evaluator: ExpressionEvaluator, fuel_rate: list[float]
    ) -> dict[str, EmissionResult]:
        """Evaluate fuel related expressions and results for a TimeSeriesCollection and a
        fuel_rate array.

        First the fuel parameters are calculated by evaluating the fuel expressions and
        the time_series object.

        Then the resulting emission volume is calculated based on the fuel rate:
        - emission_rate = emission_factor * fuel_rate

        This is done per time period and all fuel related results both in terms of
        fuel types and time periods, are merged into one common fuel collection results object.

        The length of the fuel_rate array must equal the length of the global list of periods.
        It is assumed that the fuel_rate array origins from calculations based on the same time_series
        object and thus will have the same length when used in this method.
        """
        logger.debug("Evaluating fuel usage and emissions")

        fuel_rate = np.asarray(fuel_rate)

        # Creating a pseudo-default dict with all the emitters as keys. This is to handle changes in a temporal model.
        emissions = {
            emission_name: EmissionResult.create_empty(name=emission_name, periods=Periods([]))
            for emission_name in {
                emission.name for _, model in self.temporal_fuel_model.items() for emission in model.emissions
            }
        }

        for temporal_period, model in self.temporal_fuel_model.items():
            if Period.intersects(temporal_period, expression_evaluator.get_period()):
                start_index, end_index = temporal_period.get_period_indices(expression_evaluator.get_periods())
                variables_map_this_period = expression_evaluator.get_subset(
                    start_index=start_index,
                    end_index=end_index,
                )
                fuel_rate_this_period = fuel_rate[start_index:end_index]
                for emission in model.emissions:
                    factor = variables_map_this_period.evaluate(expression=emission.factor)

                    emission_rate_kg_per_day = fuel_rate_this_period * factor
                    emission_rate_tons_per_day = Unit.KILO_PER_DAY.to(Unit.TONS_PER_DAY)(emission_rate_kg_per_day)

                    result = EmissionResult(
                        name=emission.name,
                        periods=variables_map_this_period.get_periods(),
                        rate=TimeSeriesStreamDayRate(
                            periods=variables_map_this_period.get_periods(),
                            values=emission_rate_tons_per_day.tolist(),
                            unit=Unit.TONS_PER_DAY,
                        ),
                    )

                    emissions[emission.name].extend(result)

                for name in emissions:
                    if name not in [emission.name for emission in model.emissions]:
                        emissions[name].extend(
                            EmissionResult.create_empty(name=name, periods=variables_map_this_period.get_periods())
                        )

        return dict(sorted(emissions.items()))

