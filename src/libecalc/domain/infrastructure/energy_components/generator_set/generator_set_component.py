from typing import Literal
from uuid import UUID

import numpy as np
from numpy.typing import NDArray

from libecalc.common.component_type import ComponentType
from libecalc.common.errors.exceptions import EcalcError, ProgrammingError
from libecalc.common.list.list_utils import array_to_list
from libecalc.common.logger import logger
from libecalc.common.temporal_model import TemporalModel
from libecalc.common.time_utils import Period, Periods
from libecalc.common.units import Unit
from libecalc.common.utils.nan_handling import clean_nan_values
from libecalc.common.utils.rates import (
    RateType,
    TimeSeriesBoolean,
    TimeSeriesFloat,
    TimeSeriesRate,
    TimeSeriesStreamDayRate,
)
from libecalc.common.variables import ExpressionEvaluator
from libecalc.core.result import EcalcModelResult, GeneratorSetResult
from libecalc.core.result.emission import EmissionResult
from libecalc.domain.energy import ComponentEnergyContext, Emitter, EnergyComponent, EnergyModel
from libecalc.domain.energy.emitter import EmissionName
from libecalc.domain.fuel import Fuel
from libecalc.domain.infrastructure.energy_components.electricity_consumer.electricity_consumer import (
    ElectricityConsumer,
)
from libecalc.domain.infrastructure.energy_components.fuel_model.fuel_model import FuelModel
from libecalc.domain.infrastructure.energy_components.generator_set import GeneratorSetModel
from libecalc.domain.infrastructure.path_id import PathID
from libecalc.domain.installation import ElectricityProducer, FuelConsumer, FuelConsumption
from libecalc.domain.regularity import Regularity
from libecalc.domain.time_series_cable_loss import TimeSeriesCableLoss
from libecalc.domain.time_series_max_usage_from_shore import TimeSeriesMaxUsageFromShore
from libecalc.dto.component_graph import ComponentGraph
from libecalc.dto.fuel_type import FuelType


class GeneratorSetEnergyComponent(Emitter, EnergyComponent, ElectricityProducer, FuelConsumer):
    """
    Represents a generator set as an energy component in the energy model.

    Handles the evaluation of energy usage, emission calculations, and integration with the energy modeling framework.
    Typically, uses a GeneratorSetModel to perform calculations for each timestep, and a FuelModel to evaluate emissions based on fuel usage.
    """

    def __init__(
        self,
        id: UUID,
        path_id: PathID,
        generator_set_model: TemporalModel[GeneratorSetModel],
        regularity: Regularity,
        expression_evaluator: ExpressionEvaluator,
        consumers: list[ElectricityConsumer],
        fuel: TemporalModel[FuelType],
        cable_loss: TimeSeriesCableLoss | None = None,
        max_usage_from_shore: TimeSeriesMaxUsageFromShore | None = None,
        component_type: Literal[ComponentType.GENERATOR_SET] = ComponentType.GENERATOR_SET,
    ):
        self._uuid = id
        self._path_id = path_id
        self.regularity = regularity
        self.expression_evaluator = expression_evaluator
        self.temporal_generator_set_model = generator_set_model
        self.fuel = fuel
        self.consumers = consumers if consumers is not None else []
        self.cable_loss = cable_loss
        self.max_usage_from_shore = max_usage_from_shore
        self.component_type = component_type
        self.consumer_results: dict[str, EcalcModelResult] = {}
        self.emission_results: dict[str, EmissionResult] | None = None

    def get_id(self) -> UUID:
        return self._uuid

    @property
    def id(self) -> str:
        return self._path_id.get_name()

    @property
    def name(self) -> str:
        return self._path_id.get_name()

    def is_fuel_consumer(self) -> bool:
        return True

    def is_electricity_consumer(self) -> bool:
        return False

    def is_provider(self) -> bool:
        return True

    def get_component_process_type(self) -> ComponentType:
        return self.component_type

    def get_name(self) -> str:
        return self._path_id.get_name()

    def evaluate_process_model(
        self,
        power_requirement: TimeSeriesFloat | None,
    ) -> GeneratorSetResult:
        """Warning! We are converting energy usage to NaN when the energy usage models has invalid periods. this will
        probably be changed soon.
        """
        logger.debug(f"Evaluating Genset: {self.name}")

        if power_requirement is None:
            raise EcalcError(title="Invalid generator set", message="No consumption for generator set")

        assert power_requirement.unit == Unit.MEGA_WATT

        if not len(power_requirement) == len(self.expression_evaluator.get_periods()):
            raise ProgrammingError(
                message=(
                    f"The length of the power requirement does not match the time vector for the generator set '{self.name}'. "
                    "Ensure that the power requirement aligns with the expected time periods."
                ),
            )

        periods = self.expression_evaluator.get_periods()
        actual_period = self.expression_evaluator.get_period()

        fuel_rate = self._evaluate_fuel_rate(
            power_requirement=power_requirement,
            periods=periods,
            actual_period=actual_period,
        )
        power_capacity_margin = self._evaluate_power_capacity_margin(
            power_requirement=power_requirement,
            periods=periods,
            actual_period=actual_period,
        )

        valid_periods = np.logical_and(~np.isnan(fuel_rate), power_capacity_margin >= 0)

        # Clean NaN values from fuel_rate
        fuel_rate = clean_nan_values(fuel_rate)

        return GeneratorSetResult(
            id=self.id,
            periods=self.expression_evaluator.get_periods(),
            is_valid=TimeSeriesBoolean(
                periods=self.expression_evaluator.get_periods(),
                values=array_to_list(valid_periods),
                unit=Unit.NONE,
            ),
            power_capacity_margin=TimeSeriesStreamDayRate(
                periods=self.expression_evaluator.get_periods(),
                values=array_to_list(power_capacity_margin),
                unit=Unit.MEGA_WATT,
            ),
            power=TimeSeriesStreamDayRate(
                periods=self.expression_evaluator.get_periods(),
                values=power_requirement.values,
                unit=Unit.MEGA_WATT,
            ),
            energy_usage=TimeSeriesStreamDayRate(
                periods=self.expression_evaluator.get_periods(),
                values=array_to_list(fuel_rate),
                unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
            ),
        )

    def evaluate_energy_usage(self, context: ComponentEnergyContext) -> dict[str, EcalcModelResult]:
        generator_set_result = self.evaluate_process_model(
            power_requirement=context.get_power_requirement(),
        )

        self.consumer_results[self.id] = EcalcModelResult(
            component_result=generator_set_result,
            models=[],
            sub_components=[],
        )

        return self.consumer_results

    def evaluate_emissions(
        self,
        energy_context: ComponentEnergyContext,
        energy_model: EnergyModel,
    ) -> dict[str, EmissionResult] | None:
        fuel_model = FuelModel(self.fuel)
        fuel_usage = energy_context.get_fuel_usage()

        assert fuel_usage is not None
        self.emission_results = fuel_model.evaluate_emissions(
            expression_evaluator=self.expression_evaluator,
            fuel_rate=fuel_usage.values,
        )

        return self.emission_results

    def _evaluate_fuel_rate(
        self,
        power_requirement: TimeSeriesFloat,
        periods: Periods,
        actual_period: Period,
    ) -> NDArray[np.float64]:
        values = power_requirement.values

        """Evaluate fuel consumption per period."""
        fuel_rate = np.full_like(power_requirement.values, fill_value=np.nan).astype(float)

        for period, model in self.temporal_generator_set_model.items():
            if Period.intersects(period, actual_period):
                # Get the index range corresponding to the current period
                start_index, end_index = period.get_period_indices(periods)

                # Loop through each timestep in this period
                for i in range(start_index, end_index):
                    fuel_rate[i] = model.evaluate_fuel_usage(values[i])
        return fuel_rate

    def _evaluate_power_capacity_margin(
        self,
        power_requirement: TimeSeriesFloat,
        periods: Periods,
        actual_period: Period,
    ) -> NDArray[np.float64]:
        """Evaluate power capacity margin per period."""
        values = power_requirement.values
        power_margin = np.zeros_like(power_requirement.values).astype(float)

        for period, model in self.temporal_generator_set_model.items():
            if Period.intersects(period, actual_period):
                # Get the index range corresponding to the current period
                start_index, end_index = period.get_period_indices(periods)

                # Loop through each timestep in this period
                for i in range(start_index, end_index):
                    power_margin[i] = model.evaluate_power_capacity_margin(values[i])
        return power_margin

    def get_graph(self) -> ComponentGraph:
        graph = ComponentGraph()
        graph.add_node(self)
        for electricity_consumer in self.consumers:
            if hasattr(electricity_consumer, "get_graph"):
                graph.add_subgraph(electricity_consumer.get_graph())
            else:
                graph.add_node(electricity_consumer)

            graph.add_edge(self.id, electricity_consumer.id)

        return graph

    def get_power_production(self) -> TimeSeriesRate:
        power = self.consumer_results[self.id].component_result.power
        assert power is not None
        if self.cable_loss is not None:
            cable_loss = np.array(self.cable_loss.get_values(), dtype=np.float64)

            power_production_values = power.values * (1 + cable_loss)
            return TimeSeriesRate(
                periods=power.periods,
                values=power_production_values,
                unit=power.unit,
                regularity=self.regularity.time_series.values,
                rate_type=RateType.STREAM_DAY,
            )
        else:
            return TimeSeriesRate.from_timeseries_stream_day_rate(power, regularity=self.regularity.time_series)

    def get_maximum_power_production(self) -> TimeSeriesRate | None:
        if self.max_usage_from_shore is None:
            return None
        max_power_production = self.max_usage_from_shore.get_values()

        return TimeSeriesRate(
            periods=self.expression_evaluator.get_periods(),
            values=max_power_production,
            unit=Unit.MEGA_WATT,
            regularity=self.regularity.time_series.values,
            rate_type=RateType.STREAM_DAY,
        )

    def get_fuel_consumption(self) -> FuelConsumption:
        fuel_rate = self.consumer_results[self.id].component_result.energy_usage
        return FuelConsumption(
            rate=TimeSeriesRate.from_timeseries_stream_day_rate(fuel_rate, regularity=self.regularity.time_series),
            fuel=self.fuel,  # type: ignore[arg-type]
        )

    def get_fuel(self) -> TemporalModel[Fuel]:
        return self.fuel

    def get_emissions(self) -> dict[EmissionName, TimeSeriesRate]:
        emissions = self.emission_results
        assert emissions is not None
        return {
            emission_name: TimeSeriesRate.from_timeseries_stream_day_rate(emission.rate, self.regularity.time_series)
            for emission_name, emission in emissions.items()
        }
