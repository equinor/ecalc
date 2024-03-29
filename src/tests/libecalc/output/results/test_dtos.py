from datetime import datetime

import pytest
from libecalc.common.errors.exceptions import IncompatibleDataError, ProgrammingError
from libecalc.common.time_utils import Frequency
from libecalc.common.units import Unit
from libecalc.presentation.exporter.dto.dtos import (
    AssetTSVPrognosis,
    TimeSeries,
    TimeSteps,
    TSVPrognosis,
)


def test_long_term_prognosis_incorrect_lengths_data_and_timesteps():
    with pytest.raises(IncompatibleDataError) as exc:
        TSVPrognosis(
            time_steps=TimeSteps(values=[datetime(2020, 1, 1)], frequency=Frequency.YEAR),
            time_series_collection={
                "randomField": TimeSeries(
                    values={datetime(2020, 1, 1): 1, datetime(2021, 1, 1): 2},
                    title="RandomField - User Friendly Name",
                    unit=Unit.GIGA_WATT_HOURS,
                )
            },
        )
    assert "Nr of timesteps in timeseries differ." in str(exc.value)


def test_long_term_prognosis_correct_instantiation():
    TSVPrognosis(
        time_steps=TimeSteps(values=[datetime(2020, 1, 1)], frequency=Frequency.YEAR),
        time_series_collection={
            "randomField": TimeSeries(
                values={datetime(2020, 1, 1): 1}, title="RandomField - User Friendly Name", unit=Unit.GIGA_WATT_HOURS
            )
        },
    )
    assert True


class TestTimeSeries:
    def test_fit_to_timesteps_extra_timestep(self):
        test = TimeSeries(
            values={datetime(2020, 1, 1): 9},
            title="RandomField - User Friendly Name",
            unit=Unit.GIGA_WATT_HOURS,
        )
        with pytest.raises(ProgrammingError):
            test.fit_to_timesteps([datetime(2020, 1, 1), datetime(2021, 1, 1)])

    def test_fit_to_timesteps_different_timestep(self):
        test = TimeSeries(
            values={datetime(2020, 1, 1): 9},
            title="RandomField - User Friendly Name",
            unit=Unit.GIGA_WATT_HOURS,
        )
        with pytest.raises(ProgrammingError):
            test.fit_to_timesteps([datetime(2021, 1, 1)])

    def test_fit_to_timesteps_same_timestep(self):
        test = TimeSeries(
            values={datetime(2020, 1, 1): 9},
            title="RandomField - User Friendly Name",
            unit=Unit.GIGA_WATT_HOURS,
        )

        assert test.fit_to_timesteps([datetime(2020, 1, 1)]) == test


class TestDeltaProfiles:
    def test_asset_tsv_prognosis_delta_profiles(self):
        reference_case = TSVPrognosis(
            time_steps=TimeSteps(values=[datetime(2020, 1, 1)], frequency=Frequency.YEAR),
            time_series_collection={
                "randomField": TimeSeries(
                    values={datetime(2020, 1, 1): 1},
                    title="RandomField - User Friendly Name",
                    unit=Unit.GIGA_WATT_HOURS,
                )
            },
        )
        asset_reference_case = AssetTSVPrognosis()
        asset_reference_case.add_tsv_prognosis("RandomField A", reference_case)

        projected_case = TSVPrognosis(
            time_steps=TimeSteps(values=[datetime(2020, 1, 1)], frequency=Frequency.YEAR),
            time_series_collection={
                "randomField": TimeSeries(
                    values={datetime(2020, 1, 1): 10},
                    title="RandomField - User Friendly Name",
                    unit=Unit.GIGA_WATT_HOURS,
                )
            },
        )
        asset_projected_case = AssetTSVPrognosis()
        asset_projected_case.add_tsv_prognosis("RandomField A", projected_case)

        asset_delta_profile_expected = AssetTSVPrognosis(
            tsv_prognoses={
                "RandomField A": TSVPrognosis(
                    time_steps=TimeSteps(values=[datetime(2020, 1, 1)], frequency=Frequency.YEAR),
                    time_series_collection={
                        "randomField": TimeSeries(
                            values={datetime(2020, 1, 1): 9},
                            title="RandomField - User Friendly Name",
                            unit=Unit.GIGA_WATT_HOURS,
                        )
                    },
                )
            }
        )

        assert (
            AssetTSVPrognosis.delta_profile(reference=asset_reference_case, other=asset_projected_case)
            == asset_delta_profile_expected
        )

    def test_reference_case_missing_column(self):
        reference_case = TSVPrognosis(
            time_steps=TimeSteps(values=[datetime(2020, 1, 1)], frequency=Frequency.YEAR),
            time_series_collection={},
        )
        asset_reference_case = AssetTSVPrognosis()
        asset_reference_case.add_tsv_prognosis("RandomField A", reference_case)

        projected_case = TSVPrognosis(
            time_steps=TimeSteps(values=[datetime(2020, 1, 1)], frequency=Frequency.YEAR),
            time_series_collection={
                "randomField": TimeSeries(
                    values={datetime(2020, 1, 1): 10},
                    title="RandomField - User Friendly Name",
                    unit=Unit.GIGA_WATT_HOURS,
                )
            },
        )
        asset_projected_case = AssetTSVPrognosis()
        asset_projected_case.add_tsv_prognosis("RandomField A", projected_case)

        asset_delta_profile_expected = AssetTSVPrognosis(
            tsv_prognoses={
                "RandomField A": TSVPrognosis(
                    time_steps=TimeSteps(values=[datetime(2020, 1, 1)], frequency=Frequency.YEAR),
                    time_series_collection={
                        "randomField": TimeSeries(
                            values={datetime(2020, 1, 1): 10},
                            title="RandomField - User Friendly Name",
                            unit=Unit.GIGA_WATT_HOURS,
                        )
                    },
                )
            }
        )

        assert (
            AssetTSVPrognosis.delta_profile(reference=asset_reference_case, other=asset_projected_case)
            == asset_delta_profile_expected
        )

    def test_projected_case_missing_column(self):
        reference_case = TSVPrognosis(
            time_steps=TimeSteps(values=[datetime(2020, 1, 1)], frequency=Frequency.YEAR),
            time_series_collection={
                "randomField": TimeSeries(
                    values={datetime(2020, 1, 1): 10},
                    title="RandomField - User Friendly Name",
                    unit=Unit.GIGA_WATT_HOURS,
                )
            },
        )
        asset_reference_case = AssetTSVPrognosis()
        asset_reference_case.add_tsv_prognosis("RandomField A", reference_case)

        projected_case = TSVPrognosis(
            time_steps=TimeSteps(values=[datetime(2020, 1, 1)], frequency=Frequency.YEAR),
            time_series_collection={},
        )
        asset_projected_case = AssetTSVPrognosis()
        asset_projected_case.add_tsv_prognosis("RandomField A", projected_case)

        asset_delta_profile_expected = AssetTSVPrognosis(
            tsv_prognoses={
                "RandomField A": TSVPrognosis(
                    time_steps=TimeSteps(values=[datetime(2020, 1, 1)], frequency=Frequency.YEAR),
                    time_series_collection={
                        "randomField": TimeSeries(
                            values={datetime(2020, 1, 1): -10},
                            title="RandomField - User Friendly Name",
                            unit=Unit.GIGA_WATT_HOURS,
                        )
                    },
                )
            }
        )

        assert (
            AssetTSVPrognosis.delta_profile(reference=asset_reference_case, other=asset_projected_case)
            == asset_delta_profile_expected
        )

    def test_projected_case_missing_timestep(self):
        reference_case = TSVPrognosis(
            time_steps=TimeSteps(values=[datetime(2020, 1, 1), datetime(2021, 1, 1)], frequency=Frequency.YEAR),
            time_series_collection={
                "randomField": TimeSeries(
                    values={datetime(2020, 1, 1): 4, datetime(2021, 1, 1): 10},
                    title="RandomField - User Friendly Name",
                    unit=Unit.GIGA_WATT_HOURS,
                )
            },
        )
        asset_reference_case = AssetTSVPrognosis()
        asset_reference_case.add_tsv_prognosis("RandomField A", reference_case)

        projected_case = TSVPrognosis(
            time_steps=TimeSteps(values=[datetime(2020, 1, 1)], frequency=Frequency.YEAR),
            time_series_collection={
                "randomField": TimeSeries(
                    values={datetime(2020, 1, 1): 10},
                    title="RandomField - User Friendly Name",
                    unit=Unit.GIGA_WATT_HOURS,
                )
            },
        )
        asset_projected_case = AssetTSVPrognosis()
        asset_projected_case.add_tsv_prognosis("RandomField A", projected_case)

        asset_delta_profile_expected = AssetTSVPrognosis(
            tsv_prognoses={
                "RandomField A": TSVPrognosis(
                    time_steps=TimeSteps(values=[datetime(2020, 1, 1)], frequency=Frequency.YEAR),
                    time_series_collection={
                        "randomField": TimeSeries(
                            values={datetime(2020, 1, 1): 6},
                            title="RandomField - User Friendly Name",
                            unit=Unit.GIGA_WATT_HOURS,
                        )
                    },
                )
            }
        )

        assert (
            AssetTSVPrognosis.delta_profile(reference=asset_reference_case, other=asset_projected_case)
            == asset_delta_profile_expected
        )
