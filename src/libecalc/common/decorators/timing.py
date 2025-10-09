"""
Register timing for methods with a decorator and store it to a local singleton service,
that we can query later to either return or store the timings.
"""

import time
from collections.abc import Callable
from functools import wraps
from typing import Any

from libecalc.common.logger import logger
from libecalc.common.services.timing_service import TimingRecord, TimingService


class Timings:
    @staticmethod
    def timing() -> Callable:
        """
        Decorator to measure the execution time of a function and store it in the TimingService.

        Args:
            func (Callable): The function to be decorated.

        Returns:
            Callable: The wrapped function with timing measurement.
        """

        def decorate(timeable: Callable):
            @wraps(timeable)
            def with_timing(self, *args: Any, **kwargs: Any) -> Any:
                timing_service = TimingService.instance()

                start_time_ns = time.time_ns()
                return_values = timeable(self, *args, **kwargs)
                end_time_ns = time.time_ns()

                elapsed_time_ns = end_time_ns - start_time_ns
                timing_service.record_timing(TimingRecord(timeable.__name__, elapsed_time_ns))

                logger.debug(f"Function {timeable.__name__} executed in {(elapsed_time_ns / 10e9):.6f} seconds")

                return return_values

            return with_timing

        return decorate
