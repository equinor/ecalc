import numpy as np
from numpy.typing import NDArray

from libecalc.common.logger import logger
from libecalc.domain.infrastructure.energy_components.legacy_consumer.system.results import (
    ConsumerSystemOperationalSettingResult,
)


def get_operational_settings_number_used_from_model_results(
    consumer_system_operational_settings_results: list[ConsumerSystemOperationalSettingResult],
) -> NDArray[np.int_]:
    """Calculate which operational setting is used and the resulting energy usage
    The operational settings are interpreted as in prioritized order, and the operational setting to use,
    is the one with the lowest index of those with capacity.
    """
    logger.debug("Evaluating which operational settings to use for each time period")
    result_length = len(consumer_system_operational_settings_results[0])
    operational_setting_used = np.full(result_length, 0)
    # Keep track of time steps that have yet to be assigned an operational setting
    remaining_indices_time_steps_outside_capacity = np.arange(result_length)

    logger.debug(
        "Initially we just assume that the first operational setting is ok. Fallback if there is only one consumer,"
        " even though it does not have capacity required."
    )

    if (
        len(consumer_system_operational_settings_results) > 1
    ):  # Otherwise the [:-1] and i + 1 will fail. A consumer system with only 1 operational setting/consumer does not make much sense either...
        for i, operational_setting_results in enumerate(consumer_system_operational_settings_results[:-1]):
            # keep the indices of the periods that is outside capacity to test on the next operational setting, if any

            indices_time_steps_outside_capacity = operational_setting_results.indices_outside_capacity
            logger.debug(
                f"Operational setting #{i} has {len(indices_time_steps_outside_capacity)} outside and {len(operational_setting_results.indices_within_capacity)} within capacity"
            )
            logger.debug(
                f"Timesteps with indices {operational_setting_results.indices_within_capacity} are within capacity."
            )
            remaining_indices_time_steps_outside_capacity = np.intersect1d(
                remaining_indices_time_steps_outside_capacity, indices_time_steps_outside_capacity
            )

            if len(remaining_indices_time_steps_outside_capacity) == 0:
                logger.debug("All time steps accounted for: Finished finding operational settings for all periods.")
                break
            else:
                logger.debug(
                    f"We have now {len(remaining_indices_time_steps_outside_capacity)}"
                    f" remaining periods for remaining operational settings."
                )

            # Assume, until proven otherwise, that the next operational setting to test is the correct one
            operational_setting_used[remaining_indices_time_steps_outside_capacity] = i + 1

    if len(remaining_indices_time_steps_outside_capacity) > 0:
        logger.debug(
            "We have exhausted all options, and just assume that the last prioritized operational setting is"
            " within capacity for remaining periods."
        )
        logger.debug(
            f"Last timestep has {len(consumer_system_operational_settings_results[-1].indices_outside_capacity)}"
            f" outside and {len(consumer_system_operational_settings_results[-1].indices_within_capacity)}"
            f" within capacity"
        )
        logger.debug(
            f"Timesteps with indices {consumer_system_operational_settings_results[-1].indices_within_capacity}"
            f" are within capacity."
        )

        if len(consumer_system_operational_settings_results[-1].indices_outside_capacity) > 0:
            logger.debug(
                f"Fallback to last operational setting failed. Last operational setting has only"
                f" {len(consumer_system_operational_settings_results[-1].indices_outside_capacity)}"
                f" of the remaining {len(remaining_indices_time_steps_outside_capacity)} within their capacity."
            )

    return operational_setting_used
