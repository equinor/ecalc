"""Tests for CompressorOperationalTimeSeries dataclass validation."""

import numpy as np
import pytest

from libecalc.domain.component_validation_error import DomainValidationException
from libecalc.domain.process.compressor.core.train.simplified_train.simplified_train_builder import (
    CompressorOperationalTimeSeries,
)


class TestCompressorOperationalTimeSeries:
    """Test validation logic for CompressorOperationalTimeSeries dataclass."""

    def test_validation_empty_data(self):
        """CompressorOperationalTimeSeries rejects empty data."""
        with pytest.raises(DomainValidationException) as exc_info:
            CompressorOperationalTimeSeries(
                rates=np.array([]),
                suction_pressures=np.array([]),
                discharge_pressures=np.array([]),
            )

        error_msg = str(exc_info.value)
        assert "empty" in error_msg.lower()
        assert "no valid timesteps" in error_msg.lower()

    def test_validation_mismatched_lengths(self):
        """CompressorOperationalTimeSeries rejects mismatched array lengths."""
        with pytest.raises(DomainValidationException) as exc_info:
            CompressorOperationalTimeSeries(
                rates=np.array([100.0, 200.0]),
                suction_pressures=np.array([20.0]),
                discharge_pressures=np.array([100.0, 120.0, 140.0]),
            )

        error_msg = str(exc_info.value)
        assert "same length" in error_msg.lower()
        assert "rates=2" in error_msg.lower()
        assert "suction_pressures=1" in error_msg.lower()
        assert "discharge_pressures=3" in error_msg.lower()

    def test_from_lists_validates(self):
        """CompressorOperationalTimeSeries.from_lists() performs validation."""
        with pytest.raises(DomainValidationException) as exc_info:
            CompressorOperationalTimeSeries.from_lists(
                rates=[],
                suction_pressure=[],
                discharge_pressure=[],
            )

        assert "empty" in str(exc_info.value).lower()

    def test_valid_creation(self):
        """CompressorOperationalTimeSeries accepts valid data."""
        time_series = CompressorOperationalTimeSeries(
            rates=np.array([100.0, 200.0]),
            suction_pressures=np.array([20.0, 25.0]),
            discharge_pressures=np.array([100.0, 120.0]),
        )

        assert len(time_series.rates) == 2
        assert len(time_series.suction_pressures) == 2
        assert len(time_series.discharge_pressures) == 2

    def test_from_lists_valid_creation(self):
        """CompressorOperationalTimeSeries.from_lists() accepts valid data."""
        time_series = CompressorOperationalTimeSeries.from_lists(
            rates=[100.0, 200.0],
            suction_pressure=[20.0, 25.0],
            discharge_pressure=[100.0, 120.0],
        )

        assert len(time_series.rates) == 2
        assert isinstance(time_series.rates, np.ndarray)
        assert time_series.rates.dtype == np.float64

    def test_frozen_dataclass(self):
        """CompressorOperationalTimeSeries is immutable."""
        time_series = CompressorOperationalTimeSeries(
            rates=np.array([100.0]),
            suction_pressures=np.array([20.0]),
            discharge_pressures=np.array([100.0]),
        )

        with pytest.raises(Exception):  # FrozenInstanceError
            time_series.rates = np.array([200.0])  # type: ignore
