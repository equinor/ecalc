from typing import Literal

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
from libecalc.common.utils.rates import TimeSeriesBoolean, TimeSeriesFloat, TimeSeriesStreamDayRate
from libecalc.common.variables import ExpressionEvaluator
from libecalc.core.result import EcalcModelResult, GeneratorSetResult
from libecalc.core.result.emission import EmissionResult
from libecalc.domain.component_validation_error import (
    ComponentValidationException,
    ModelValidationError,
)
from libecalc.domain.energy import ComponentEnergyContext, Emitter, EnergyComponent, EnergyModel
from libecalc.domain.infrastructure.energy_components.electricity_consumer.electricity_consumer import (
    ElectricityConsumer,
)
from libecalc.domain.infrastructure.energy_components.fuel_consumer.fuel_consumer import FuelConsumer
from libecalc.domain.infrastructure.energy_components.fuel_model.fuel_model import FuelModel
from libecalc.domain.infrastructure.energy_components.generator_set import GeneratorSetModel
from libecalc.domain.infrastructure.energy_components.utils import _convert_keys_in_dictionary_from_str_to_periods
from libecalc.domain.infrastructure.path_id import PathID
from libecalc.domain.regularity import Regularity
from libecalc.dto.component_graph import ComponentGraph
from libecalc.dto.fuel_type import FuelType
from libecalc.dto.types import ConsumerUserDefinedCategoryType
from libecalc.dto.utils.validators import (
    ExpressionType,
    validate_temporal_model,
)
from libecalc.presentation.yaml.validation_errors import Location


class GeneratorSetEnergyComponent(Emitter, EnergyComponent):
    """
    Represents a generator set as an energy component in the energy model.

    Handles the evaluation of energy usage, emission calculations, and integration with the energy modeling framework.
    Typically, uses a GeneratorSetModel to perform calculations for each timestep, and a FuelModel to evaluate emissions based on fuel usage.
    """

    def __init__(
        self,
        path_id: PathID,
        user_defined_category: dict[Period, ConsumerUserDefinedCategoryType],
        generator_set_model: dict[Period, GeneratorSetModel],
        regularity: Regularity,
        expression_evaluator: ExpressionEvaluator,
        consumers: list[ElectricityConsumer] = None,
        fuel: dict[Period, FuelType] = None,
        cable_loss: ExpressionType | None = None,
        max_usage_from_shore: ExpressionType | None = None,
        component_type: Literal[ComponentType.GENERATOR_SET] = ComponentType.GENERATOR_SET,
    ):
        self._path_id = path_id
        self.user_defined_category = user_defined_category
        self.regularity = regularity
        self.expression_evaluator = expression_evaluator
        self.generator_set_model = self.check_generator_set_model(generator_set_model)
        self.temporal_generator_set_model = TemporalModel(self.generator_set_model)
        self.fuel = self.check_fuel(fuel)
        self.consumers = consumers if consumers is not None else []
        self.cable_loss = cable_loss
        self.max_usage_from_shore = max_usage_from_shore
        self.component_type = component_type
        self._validate_genset_temporal_models(self.generator_set_model, self.fuel)
        self.check_consumers()
        self.consumer_results: dict[str, EcalcModelResult] = {}
        self.emission_results: dict[str, EmissionResult] | None = None

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

    @staticmethod
    def _validate_genset_temporal_models(
        generator_set_model: dict[Period, GeneratorSetModel], fuel: dict[Period, FuelType]
    ):
        validate_temporal_model(generator_set_model)
        validate_temporal_model(fuel)

    @staticmethod
    def check_generator_set_model(generator_set_model: dict[Period, GeneratorSetModel]):
        if isinstance(generator_set_model, dict) and len(generator_set_model.values()) > 0:
            generator_set_model = _convert_keys_in_dictionary_from_str_to_periods(generator_set_model)
        return generator_set_model

    def check_fuel(self, fuel: dict[Period, FuelType]):
        """
        Make sure that temporal models are converted to Period objects if they are strings,
        and that fuel is set
        """
        if isinstance(fuel, dict) and len(fuel.values()) > 0:
            fuel = _convert_keys_in_dictionary_from_str_to_periods(fuel)
        if self.is_fuel_consumer() and (fuel is None or len(fuel) < 1):
            msg = "Missing fuel for generator set"
            raise ComponentValidationException(
                errors=[
                    ModelValidationError(
                        name=self.name,
                        location=Location([self.name]),  # for now, we will use the name as the location
                        message=str(msg),
                    )
                ],
            )
        return fuel

    def check_consumers(self):
        errors: list[ModelValidationError] = []
        for consumer in self.consumers:
            if isinstance(consumer, FuelConsumer):
                errors.append(
                    ModelValidationError(
                        name=consumer.name,
                        message="The consumer is not an electricity consumer. Generators can not have fuel consumers.",
                        location=Location([consumer.name]),  # for now, we will use the name as the location
                    )
                )

        if errors:
            raise ComponentValidationException(errors=errors)

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
