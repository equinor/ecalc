import abc

import numpy as np
from numpy.typing import NDArray

from libecalc.common.logger import logger
from libecalc.domain.component_validation_error import DomainValidationException
from libecalc.domain.infrastructure.energy_components.legacy_consumer.consumer_function import ConsumerFunction
from libecalc.domain.infrastructure.energy_components.legacy_consumer.system.operational_setting import (
    ConsumerSystemOperationalSettingExpressions,
)
from libecalc.domain.infrastructure.energy_components.legacy_consumer.system.results import (
    ConsumerSystemOperationalSettingResult,
)
from libecalc.domain.infrastructure.energy_components.legacy_consumer.system.utils import (
    get_operational_settings_number_used_from_model_results,
)
from libecalc.domain.process.core.results import EnergyFunctionResult
from libecalc.domain.process.evaluation_input import ConsumerSystemOperationalInput
from libecalc.domain.time_series_power_loss_factor import TimeSeriesPowerLossFactor


class SystemComponent(abc.ABC):
    @property
    @abc.abstractmethod
    def name(self) -> str: ...

    @abc.abstractmethod
    def get_max_standard_rate(
        self,
        suction_pressure: NDArray[np.float64],
        discharge_pressure: NDArray[np.float64],
        fluid_density: NDArray[np.float64] = None,
    ): ...

    @abc.abstractmethod
    def evaluate(
        self,
        rate: NDArray[np.float64],
        suction_pressure: NDArray[np.float64],
        discharge_pressure: NDArray[np.float64],
        fluid_density: NDArray[np.float64] = None,
    ) -> EnergyFunctionResult: ...


class ConsumerSystemConsumerFunction(ConsumerFunction):
    def __init__(
        self,
        consumer_components: list[SystemComponent],
        operational_settings_expressions: list[ConsumerSystemOperationalSettingExpressions],
        power_loss_factor: TimeSeriesPowerLossFactor | None,
    ):
        """operational_settings_expressions, condition_expression and power_loss_factor_expression
        defines one expression per time-step.
        NOTE: Only used for pumps, therefore explicit use of fluid density in operational settings.
        """
        self.consumers = consumer_components
        self._operational_settings_expressions = operational_settings_expressions
        self.power_loss_factor = power_loss_factor
        self.validate()

    def validate(self):
        for operational_settings_expression in self._operational_settings_expressions:
            if operational_settings_expression.number_of_consumers != len(self.consumers):
                message = (
                    f"Number of consumers in operational setting "
                    f"({operational_settings_expression.number_of_consumers})"
                    f" does not match the number of consumers in the consumer system ({len(self.consumers)})"
                )
                logger.error(message)
                raise DomainValidationException(message=message)

    @property
    def operational_settings(self) -> list[ConsumerSystemOperationalSettingExpressions]:
        return self._operational_settings_expressions

    @property
    def number_of_consumers(self) -> int:
        return len(self.consumers)

    def evaluate(self) -> ConsumerSystemOperationalInput:
        """
        Apply cross-over adjustments in operational settings and assemble
        the operational input for the consumer system, to be used for further evaluation of
        the individual consumers in the system.

        The operational input includes the actual operational settings used (adjusted for cross-over),
        whether cross-over was used at each time step, and the indices of the operational settings
        used for each time step.

        Returns:
            ConsumerSystemOperationalInput: The operational settings and
            cross-over usage for each time step.
        """

        self._adjust_operational_settings_for_cross_over()
        system_operational_input = self._get_system_operational_input()

        return system_operational_input

    def _calculate_operational_settings_after_cross_over(
        self,
        operational_setting: ConsumerSystemOperationalSettingExpressions,
    ):
        """Calculate rates after cross over is applied for consumers. Does not check if the
        "receiving" consumer now get a rate within it's capacity, just set rate of "sender"
        equal to it's maximum rate and add the rest to the "receiver".
        """
        cross_over_specification = operational_setting.cross_overs or [0] * len(self.consumers)

        rates_after_cross_over = [
            np.array(rate.get_stream_day_values(), copy=True) for rate in operational_setting.rates
        ]
        for consumer_index, cross_over_number in enumerate(cross_over_specification):
            if cross_over_number == 0:
                continue
            consumer_discharge_pressure = operational_setting.get_discharge_pressure(consumer_index)
            receiver_discharge_pressure = operational_setting.get_discharge_pressure(cross_over_number - 1)
            consumer_maximum_rate = self.consumers[consumer_index].get_max_standard_rate(
                suction_pressure=operational_setting.get_suction_pressure(consumer_index),
                discharge_pressure=consumer_discharge_pressure,
                fluid_density=operational_setting.get_fluid_density(consumer_index),
            )

            transfer_rate = operational_setting.get_rate(consumer_index) - consumer_maximum_rate
            # Only transfer when max rate is exceeded
            transfer_rate = np.where(transfer_rate > 0, transfer_rate, 0)

            # Only transfer when the receiver discharge pressure >= sender discharge pressure
            transfer_rate = np.where(receiver_discharge_pressure >= consumer_discharge_pressure, transfer_rate, 0)

            # Subtract transfer rate on current consumer
            rates_after_cross_over[consumer_index] -= transfer_rate
            # Add transfer rate to receiving consumer
            rates_after_cross_over[cross_over_number - 1] += transfer_rate

        operational_setting.set_rates_after_crossover(rates_after_cross_over)

    def _get_system_operational_input(self) -> ConsumerSystemOperationalInput:
        num_consumers = len(self.consumers)
        # Pre-evaluate all operational settings
        operational_settings_results = self._evaluate_all_operational_settings()

        # Find which operational setting is used for each time step
        used_setting_indices = get_operational_settings_number_used_from_model_results(
            consumer_system_operational_settings_results=operational_settings_results
        )

        # Initialize dict for the 'selected' operational settings, operational settings used (actual values, not index).
        actual_operational_settings: dict[int, dict[str, list[float]]] = {
            consumer_index: {
                "rate": [],
                "suction_pressure": [],
                "discharge_pressure": [],
                "fluid_density": [],
            }
            for consumer_index in range(num_consumers)
        }

        crossover_used: list[bool] = []
        # Assemble the actual operational settings and determine crossover usage
        # for each time step based on the selected operational setting:
        for time_index, used_setting_index in enumerate(used_setting_indices):
            operational_setting = self.operational_settings[used_setting_index]

            for consumer_index in range(num_consumers):
                actual_operational_settings[consumer_index]["rate"].append(
                    operational_setting.get_rate_after_crossover(consumer_index)[time_index]
                )
                actual_operational_settings[consumer_index]["suction_pressure"].append(
                    operational_setting.get_suction_pressure(consumer_index)[time_index]
                )
                actual_operational_settings[consumer_index]["discharge_pressure"].append(
                    operational_setting.get_discharge_pressure(consumer_index)[time_index]
                )
                fluid_density = operational_setting.get_fluid_density(consumer_index)
                actual_operational_settings[consumer_index]["fluid_density"].append(
                    fluid_density[time_index] if isinstance(fluid_density, np.ndarray) else fluid_density
                )
            crossover_rates_per_consumer = [
                operational_setting.get_crossover_rate(consumer_index)[time_index]
                for consumer_index in range(num_consumers)
            ]
            crossover_used.append(any(cross > 0 for cross in crossover_rates_per_consumer))

        return ConsumerSystemOperationalInput(
            actual_operational_settings=actual_operational_settings,
            crossover_used=crossover_used,
            operational_setting_number_used_per_timestep=used_setting_indices,
            periods=self.operational_settings[0].rates[0].get_periods(),
        )

    def _adjust_operational_settings_for_cross_over(self):
        operational_settings = self.operational_settings
        for operational_setting in operational_settings:
            if operational_setting.cross_overs:
                self._calculate_operational_settings_after_cross_over(
                    operational_setting=operational_setting,
                )

    def _evaluate_all_operational_settings(self) -> list[ConsumerSystemOperationalSettingResult]:
        """
        Evaluates all operational settings for the consumer system.

        This method performs a pre-evaluation of each consumer in the system for each
        operational setting by running all consumers with their respective parameters.
        The results are used to determine which operational setting is used for each timestep
        in subsequent processing.

        Returns:
            list[ConsumerSystemOperationalSettingResult]: Results for each operational setting.
        """

        results = []
        for i, operational_setting in enumerate(self.operational_settings):
            logger.debug(f"Evaluating operational setting #{i}")
            consumer_results: dict[str, EnergyFunctionResult] = {}
            for consumer_index, consumer in enumerate(self.consumers):
                consumer_result: EnergyFunctionResult = consumer.evaluate(
                    rate=operational_setting.get_rate_after_crossover(consumer_index),
                    suction_pressure=operational_setting.get_suction_pressure(consumer_index),
                    discharge_pressure=operational_setting.get_discharge_pressure(consumer_index),
                    fluid_density=operational_setting.get_fluid_density(consumer_index),
                )
                consumer_results[consumer.name] = consumer_result
            results.append(
                ConsumerSystemOperationalSettingResult(
                    consumer_results=list(consumer_results.values()),
                )
            )
        return results
