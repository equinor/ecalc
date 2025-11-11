from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from libecalc.domain.time_series_flow_rate import TimeSeriesFlowRate
from libecalc.domain.time_series_pressure import TimeSeriesPressure


@dataclass(frozen=True)
class CompressorOperationalTimeSeries:
    """Time series data for compressor stage preparation.

    Contains operational data (rates, suction pressure, discharge pressure)
    for all timesteps in a period. Used to prepare simplified compressor train stages.

    Validation is performed in __post_init__ to ensure data integrity.

    Note:
    - Arrays are never filtered by CONDITION - validation_mask is handled separately
    """

    rates: NDArray[np.float64]
    suction_pressures: NDArray[np.float64] | None
    discharge_pressures: NDArray[np.float64] | None

    @classmethod
    def from_time_series(
        cls,
        rates: TimeSeriesFlowRate,
        suction_pressure: TimeSeriesPressure | None,
        discharge_pressure: TimeSeriesPressure | None,
    ) -> CompressorOperationalTimeSeries:
        """Create from Python lists (converts to numpy arrays).

        Args:
            rates: Flow rates [Sm3/day]
            suction_pressure: Suction pressures [bara]
            discharge_pressure: Discharge pressures [bara]

        Returns:
            CompressorOperationalTimeSeries with validated data

        Raises:
            DomainValidationException: If data is empty or arrays have mismatched lengths
        """
        return cls(
            rates=np.asarray(rates.get_stream_day_values(), dtype=np.float64),
            suction_pressures=np.asarray(suction_pressure.get_values(), dtype=np.float64)
            if suction_pressure is not None
            else None,
            discharge_pressures=np.asarray(discharge_pressure.get_values(), dtype=np.float64)
            if discharge_pressure is not None
            else None,
        )


def calculate_number_of_stages(
    maximum_pressure_ratio_per_stage: float,
    discharge_pressures: NDArray[np.float64],
    suction_pressures: NDArray[np.float64],
) -> int:
    """Prepare stages for unknown stages simplified model from time series data.

    Args:
        suction_pressures:
        discharge_pressures:
        maximum_pressure_ratio_per_stage: Maximum pressure ratio per stage

    Returns:
        List of prepared CompressorTrainStage objects with charts
    """
    # Calculate number of stages needed based on maximum pressure ratio
    pressure_ratios = discharge_pressures / suction_pressures
    maximum_train_pressure_ratio = max(pressure_ratios)

    x = math.log(maximum_train_pressure_ratio) / math.log(maximum_pressure_ratio_per_stage)
    return math.ceil(x)
