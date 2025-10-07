"""Tests for envelope extraction in simplified compressor models.

Envelope extraction concatenates time series data from operational settings
to create compressor stages that work across all conditions.
"""

import numpy as np
import pytest
from numpy.typing import NDArray

from libecalc.common.time_utils import Periods
from libecalc.domain.infrastructure.energy_components.legacy_consumer.system.operational_setting import (
    ConsumerSystemOperationalSettingExpressions,
)
from libecalc.domain.process.compressor.core.train.simplified_train.envelope_extractor import EnvelopeExtractor
from libecalc.domain.process.compressor.core.train.simplified_train.exceptions import EmptyEnvelopeException
from libecalc.domain.time_series_flow_rate import TimeSeriesFlowRate
from libecalc.domain.time_series_pressure import TimeSeriesPressure


class MockTimeSeriesFlowRate(TimeSeriesFlowRate):
    """Mock flow rate time series for testing."""

    def __init__(self, values: NDArray[np.float64]):
        self.values = values

    def get_stream_day_values(self) -> list[float]:
        return self.values.tolist()

    def get_periods(self) -> Periods:
        return Periods.create_periods([], include_before=False, include_after=False)


class MockTimeSeriesPressure(TimeSeriesPressure):
    """Mock pressure time series for testing."""

    def __init__(self, values: NDArray[np.float64]):
        self.values = values

    def get_values(self) -> list[float]:
        return self.values.tolist()

    def get_periods(self) -> Periods:
        return Periods.create_periods([], include_before=False, include_after=False)


class TestEnvelopeExtractor:
    """Test envelope extraction for simplified compressor models."""

    def test_single_train_multiple_settings(self):
        """Single train envelope concatenates data from all operational settings."""
        setting1 = ConsumerSystemOperationalSettingExpressions(
            rates=[MockTimeSeriesFlowRate(np.array([100.0, 200.0]))],
            suction_pressures=[MockTimeSeriesPressure(np.array([20.0, 25.0]))],
            discharge_pressures=[MockTimeSeriesPressure(np.array([100.0, 120.0]))],
        )
        setting2 = ConsumerSystemOperationalSettingExpressions(
            rates=[MockTimeSeriesFlowRate(np.array([300.0, 400.0]))],
            suction_pressures=[MockTimeSeriesPressure(np.array([30.0, 35.0]))],
            discharge_pressures=[MockTimeSeriesPressure(np.array([140.0, 160.0]))],
        )

        extractor = EnvelopeExtractor()
        envelope = extractor.extract_envelope_for_model_reference(
            operational_settings=[setting1, setting2], compressor_indices=[0]
        )

        assert len(envelope.rates) == 4
        assert min(envelope.rates) == 100.0
        assert max(envelope.rates) == 400.0

    def test_filters_invalid_data(self):
        """NaN and zero/negative pressures are filtered out."""
        setting = ConsumerSystemOperationalSettingExpressions(
            rates=[MockTimeSeriesFlowRate(np.array([100.0, np.nan, 300.0]))],
            suction_pressures=[MockTimeSeriesPressure(np.array([20.0, 0.0, 30.0]))],
            discharge_pressures=[MockTimeSeriesPressure(np.array([100.0, 120.0, 140.0]))],
        )

        extractor = EnvelopeExtractor()
        envelope = extractor.extract_envelope_for_model_reference(
            operational_settings=[setting], compressor_indices=[0]
        )

        assert len(envelope.rates) == 2
        assert 100.0 in envelope.rates
        assert 300.0 in envelope.rates

    def test_identical_trains_combined_envelope(self):
        """Two trains pointing to same model get combined envelope.

        When two trains reference the same COMPRESSOR_MODEL, their operational
        envelopes must be combined so they use identical stages.
        """
        setting1 = ConsumerSystemOperationalSettingExpressions(
            rates=[
                MockTimeSeriesFlowRate(np.array([1000.0])),  # Train 0
                MockTimeSeriesFlowRate(np.array([500.0])),  # Train 1
            ],
            suction_pressures=[
                MockTimeSeriesPressure(np.array([20.0])),
                MockTimeSeriesPressure(np.array([25.0])),
            ],
            discharge_pressures=[
                MockTimeSeriesPressure(np.array([100.0])),
                MockTimeSeriesPressure(np.array([120.0])),
            ],
        )
        setting2 = ConsumerSystemOperationalSettingExpressions(
            rates=[
                MockTimeSeriesFlowRate(np.array([1200.0])),
                MockTimeSeriesFlowRate(np.array([600.0])),
            ],
            suction_pressures=[
                MockTimeSeriesPressure(np.array([22.0])),
                MockTimeSeriesPressure(np.array([27.0])),
            ],
            discharge_pressures=[
                MockTimeSeriesPressure(np.array([110.0])),
                MockTimeSeriesPressure(np.array([130.0])),
            ],
        )

        extractor = EnvelopeExtractor()
        envelope = extractor.extract_envelope_for_model_reference(
            operational_settings=[setting1, setting2], compressor_indices=[0, 1]
        )

        # Combined envelope: 2 trains × 2 settings = 4 data points
        assert len(envelope.rates) == 4
        assert set(envelope.rates) == {500.0, 600.0, 1000.0, 1200.0}

    def test_identical_trains_single_setting(self):
        """Two trains with single operational setting."""
        setting = ConsumerSystemOperationalSettingExpressions(
            rates=[
                MockTimeSeriesFlowRate(np.array([100.0, 200.0])),
                MockTimeSeriesFlowRate(np.array([150.0, 250.0])),
            ],
            suction_pressures=[
                MockTimeSeriesPressure(np.array([20.0, 25.0])),
                MockTimeSeriesPressure(np.array([22.0, 27.0])),
            ],
            discharge_pressures=[
                MockTimeSeriesPressure(np.array([100.0, 120.0])),
                MockTimeSeriesPressure(np.array([110.0, 130.0])),
            ],
        )

        extractor = EnvelopeExtractor()
        envelope = extractor.extract_envelope_for_model_reference(
            operational_settings=[setting], compressor_indices=[0, 1]
        )

        assert len(envelope.rates) == 4
        assert min(envelope.rates) == 100.0
        assert max(envelope.rates) == 250.0

    def test_partial_overlap_three_trains(self):
        """Three trains where two share same model reference.

        Simulates: Train 0 and 2 use 'export_compressor_reference',
        Train 1 uses 'injection_compressor_reference'
        """
        setting = ConsumerSystemOperationalSettingExpressions(
            rates=[
                MockTimeSeriesFlowRate(np.array([100.0])),
                MockTimeSeriesFlowRate(np.array([200.0])),
                MockTimeSeriesFlowRate(np.array([150.0])),
            ],
            suction_pressures=[
                MockTimeSeriesPressure(np.array([20.0])),
                MockTimeSeriesPressure(np.array([30.0])),
                MockTimeSeriesPressure(np.array([25.0])),
            ],
            discharge_pressures=[
                MockTimeSeriesPressure(np.array([100.0])),
                MockTimeSeriesPressure(np.array([150.0])),
                MockTimeSeriesPressure(np.array([120.0])),
            ],
        )

        extractor = EnvelopeExtractor()

        # Trains 0 and 2 share model reference
        envelope_export = extractor.extract_envelope_for_model_reference(
            operational_settings=[setting], compressor_indices=[0, 2]
        )
        assert len(envelope_export.rates) == 2
        assert set(envelope_export.rates) == {100.0, 150.0}

        # Train 1 has unique model reference
        envelope_injection = extractor.extract_envelope_for_model_reference(
            operational_settings=[setting], compressor_indices=[1]
        )
        assert len(envelope_injection.rates) == 1
        assert envelope_injection.rates[0] == 200.0

    def test_empty_indices_raises_error(self):
        """Empty compressor_indices list raises ValueError."""
        setting = ConsumerSystemOperationalSettingExpressions(
            rates=[MockTimeSeriesFlowRate(np.array([100.0]))],
            suction_pressures=[MockTimeSeriesPressure(np.array([20.0]))],
            discharge_pressures=[MockTimeSeriesPressure(np.array([100.0]))],
        )

        extractor = EnvelopeExtractor()

        with pytest.raises(ValueError, match="compressor_indices list is empty"):
            extractor.extract_envelope_for_model_reference(operational_settings=[setting], compressor_indices=[])

    def test_filters_invalid_data_multiple_trains(self):
        """Filters NaN and invalid pressures from all trains."""
        setting = ConsumerSystemOperationalSettingExpressions(
            rates=[
                MockTimeSeriesFlowRate(np.array([100.0, np.nan, 300.0])),
                MockTimeSeriesFlowRate(np.array([200.0, 400.0, 500.0])),
            ],
            suction_pressures=[
                MockTimeSeriesPressure(np.array([20.0, 0.0, 30.0])),
                MockTimeSeriesPressure(np.array([25.0, 35.0, np.nan])),
            ],
            discharge_pressures=[
                MockTimeSeriesPressure(np.array([100.0, 120.0, 140.0])),
                MockTimeSeriesPressure(np.array([120.0, 160.0, 180.0])),
            ],
        )

        extractor = EnvelopeExtractor()
        envelope = extractor.extract_envelope_for_model_reference(
            operational_settings=[setting], compressor_indices=[0, 1]
        )

        # Valid entries: train0[0,2] + train1[0,1] = 4 entries
        assert len(envelope.rates) == 4
        assert set(envelope.rates) == {100.0, 200.0, 300.0, 400.0}

    def test_no_valid_data_raises_empty_envelope_exception(self):
        """When all data is invalid, raises EmptyEnvelopeException with context."""
        setting = ConsumerSystemOperationalSettingExpressions(
            rates=[MockTimeSeriesFlowRate(np.array([np.nan, np.nan]))],
            suction_pressures=[MockTimeSeriesPressure(np.array([0.0, -5.0]))],
            discharge_pressures=[MockTimeSeriesPressure(np.array([100.0, 120.0]))],
        )

        extractor = EnvelopeExtractor()

        with pytest.raises(EmptyEnvelopeException) as exc_info:
            extractor.extract_envelope_for_model_reference(
                operational_settings=[setting],
                compressor_indices=[0],
                model_reference_for_error_context="test_compressor_model",
            )

        # Verify exception contains helpful context
        error_msg = str(exc_info.value)
        assert "test_compressor_model" in error_msg
        assert "[0]" in error_msg  # compressor indices
        assert "No valid operational data" in error_msg
        assert "may be caused by" in error_msg.lower()
