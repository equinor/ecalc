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
    ConsumerSystemConsumerFunctionResult,
    ConsumerSystemOperationalSettingResult,
    SystemComponentResultWithName,
)
from libecalc.domain.infrastructure.energy_components.legacy_consumer.system.utils import (
    get_operational_settings_number_used_from_model_results,
)
from libecalc.domain.process.core.results import EnergyFunctionResult
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

    def evaluate(self) -> ConsumerSystemConsumerFunctionResult:
        """Steps in evaluating a consumer system:

        1. Convert operational settings from expressions to values
        2. Adjust operational settings for cross-overs (pre-processing)
        3. Evaluate condition from expressions to values
        4. Apply condition to operational settings
        5. Evaluate the consumer systems with the different operational settings
        6. Assemble the settings number used for each time step
        7. Assemble the operational setting based on 4.
        8. Evaluate of cross-over has been used.
        9. Run the consumers with the resulting Operational settings in 5.
        10. Compute the sum of energy and power used by the consumers
        11. Evaluate and apply power loss expressions
        12. Return a complete ConsumerSystemConsumerFunctionResult with data from the above steps.
        """
        operational_settings = self.operational_settings

        for operational_setting in operational_settings:
            if operational_setting.cross_overs:
                self.calculate_operational_settings_after_cross_over(
                    operational_setting=operational_setting,
                )

        consumer_system_operational_settings_results = []
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

            consumer_system_operational_settings_results.append(
                ConsumerSystemOperationalSettingResult(
                    consumer_results=list(consumer_results.values()),
                )
            )

        operational_setting_number_used_per_timestep = get_operational_settings_number_used_from_model_results(
            consumer_system_operational_settings_results=consumer_system_operational_settings_results
        )

        crossover_used = []

        # The 'selected' operational settings, operational settings used (actual values, not index).
        actual_operational_settings: dict[int, dict[str, list[float]]] = {
            consumer_index: {
                "rate": [],
                "suction_pressure": [],
                "discharge_pressure": [],
                "fluid_density": [],
            }
            for consumer_index in range(len(self.consumers))
        }
        for index, operational_setting_used in enumerate(operational_setting_number_used_per_timestep):
            operational_setting = self.operational_settings[operational_setting_used]

            crossover_per_consumer = []
            for consumer_index in range(len(self.consumers)):
                crossover_per_consumer.append(operational_setting.get_crossover_rate(consumer_index)[index])

                op_settings_for_consumer = actual_operational_settings[consumer_index]
                op_settings_for_consumer["rate"].append(
                    operational_setting.get_rate_after_crossover(consumer_index)[index]
                )
                op_settings_for_consumer["suction_pressure"].append(
                    operational_setting.get_suction_pressure(consumer_index)[index]
                )
                op_settings_for_consumer["discharge_pressure"].append(
                    operational_setting.get_discharge_pressure(consumer_index)[index]
                )
                fluid_density = operational_setting.get_fluid_density(consumer_index)
                op_settings_for_consumer["fluid_density"].append(
                    fluid_density[index] if isinstance(fluid_density, np.ndarray) else fluid_density
                )

            crossover_used.append(any(cross > 0 for cross in crossover_per_consumer))

        # TODO: Calculating again only to avoid having to construct results?
        actual_component_results: list[EnergyFunctionResult] = []
        for consumer_index, consumer in enumerate(self.consumers):
            op_setting = actual_operational_settings[consumer_index]
            r = consumer.evaluate(
                rate=np.asarray(op_setting["rate"]),
                suction_pressure=np.asarray(op_setting["suction_pressure"]),
                discharge_pressure=np.asarray(op_setting["discharge_pressure"]),
                fluid_density=np.asarray(op_setting["fluid_density"]),
            )
            actual_component_results.append(r)

        periods = self.operational_settings[0].rates[0].get_periods()

        consumer_results_with_name = [
            SystemComponentResultWithName(name=consumer.name, result=result)
            for consumer, result in zip(self.consumers, actual_component_results)
        ]

        return ConsumerSystemConsumerFunctionResult(
            periods=periods,
            operational_setting_used=operational_setting_number_used_per_timestep,
            consumer_results=consumer_results_with_name,
            cross_over_used=np.asarray(crossover_used),
            power_loss_factor=self.power_loss_factor,
        )

    def calculate_operational_settings_after_cross_over(
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
