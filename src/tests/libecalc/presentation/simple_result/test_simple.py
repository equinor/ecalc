from copy import deepcopy
from datetime import datetime

from libecalc.common.component_info.component_level import ComponentLevel
from libecalc.common.component_type import ComponentType
from libecalc.common.time_utils import Periods
from libecalc.common.units import Unit
from libecalc.presentation.simple_result.simple import (
    SimpleComponentResult,
    SimpleEmissionResult,
    SimpleResultData,
)


class TestDeltaProfile:
    def test_common_timesteps_common_components(self):
        periods = Periods.create_periods(
            times=[datetime(2020, 1, 1), datetime(2021, 1, 1), datetime(2022, 1, 1), datetime(2023, 1, 1)],
            include_before=False,
            include_after=False,
        )
        reference_model = SimpleResultData(
            periods=periods,
            components=[
                SimpleComponentResult(
                    name="component1",
                    parent="installation1",
                    componentType=ComponentType.COMPRESSOR,
                    component_level=ComponentLevel.CONSUMER,
                    periods=periods,
                    emissions={
                        "co2": SimpleEmissionResult(
                            name="co2",
                            rate=[3, 4, 5],
                        )
                    },
                    energy_usage=[2, 3, 4],
                    energy_usage_unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                    power=[7, 8, 9],
                    is_valid=[True] * len(periods),
                )
            ],
        )

        other_model = SimpleResultData(
            periods=periods,
            components=[
                SimpleComponentResult(
                    name="component1",
                    parent="installation1",
                    componentType=ComponentType.COMPRESSOR,
                    component_level=ComponentLevel.CONSUMER,
                    periods=periods,
                    emissions={
                        "co2": SimpleEmissionResult(
                            name="co2",
                            rate=[6, 8, 10],
                        )
                    },
                    energy_usage=[4, 6, 8],
                    energy_usage_unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                    power=[14, 16, 18],
                    is_valid=[True] * len(periods),
                )
            ],
        )
        other_model, reference_model, delta_profile, errors = SimpleResultData.delta_profile(
            reference_model,
            other_model,
        )
        assert delta_profile == reference_model
        assert len(errors) == 0

    def test_common_timesteps_different_components(self):
        """Test that missing components is treated as zero,
        i.e. missing_component - reference_component = -1 * reference_component and
             changed_component - missing_component = changed_component.
        """
        periods = Periods.create_periods(
            times=[datetime(2020, 1, 1), datetime(2021, 1, 1), datetime(2022, 1, 1), datetime(2023, 1, 1)],
            include_before=False,
            include_after=False,
        )
        reference_model = SimpleResultData(
            periods=periods,
            components=[
                SimpleComponentResult(
                    name="component1",
                    parent="installation1",
                    componentType=ComponentType.COMPRESSOR,
                    component_level=ComponentLevel.CONSUMER,
                    periods=periods,
                    emissions={
                        "co2": SimpleEmissionResult(
                            name="co2",
                            rate=[3, 4, 5],
                        )
                    },
                    energy_usage=[2, 3, 4],
                    energy_usage_unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                    power=[7, 8, 9],
                    is_valid=[True] * len(periods),
                )
            ],
        )

        component_2 = SimpleComponentResult(
            name="component2",
            parent="installation1",
            componentType=ComponentType.COMPRESSOR,
            component_level=ComponentLevel.CONSUMER,
            periods=periods,
            emissions={
                "co2": SimpleEmissionResult(
                    name="co2",
                    rate=[6, 8, 10],
                )
            },
            energy_usage=[4, 6, 8],
            energy_usage_unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
            power=[14, 16, 18],
            is_valid=[True] * len(periods),
        )

        other_model = SimpleResultData(periods=periods, components=[component_2])
        other_model, reference_model, delta_profile, errors = SimpleResultData.delta_profile(
            reference_model,
            other_model,
        )
        assert len(errors) == 0
        assert delta_profile == SimpleResultData(
            periods=periods,
            components=[
                SimpleComponentResult(
                    name="component1",
                    parent="installation1",
                    componentType=ComponentType.COMPRESSOR,
                    component_level=ComponentLevel.CONSUMER,
                    periods=periods,
                    emissions={
                        "co2": SimpleEmissionResult(
                            name="co2",
                            rate=[-3, -4, -5],
                        )
                    },
                    energy_usage=[-2, -3, -4],
                    energy_usage_unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                    power=[-7, -8, -9],
                    is_valid=[True] * len(periods),
                ),
                component_2,
            ],
        )

    def test_different_periods_common_components_common_first_and_last_dates(self):
        """The model with the coarsest periods will be split to get values at the same places as the other model.
        Here the period covering 2020 - 2022 will be split in two equal models (2020-2021 and 2021-2022) for the
        reference model to match the periods in the changed model."""
        reference_timesteps = [datetime(2020, 1, 1), datetime(2022, 1, 1), datetime(2023, 1, 1)]
        periods = Periods.create_periods(
            times=reference_timesteps,
            include_before=False,
            include_after=False,
        )
        reference_model = SimpleResultData(
            periods=periods,
            components=[
                SimpleComponentResult(
                    name="component1",
                    parent="installation1",
                    componentType=ComponentType.COMPRESSOR,
                    component_level=ComponentLevel.CONSUMER,
                    periods=periods,
                    emissions={
                        "co2": SimpleEmissionResult(
                            name="co2",
                            rate=[3, 5],
                        )
                    },
                    energy_usage=[2, 4],
                    energy_usage_unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                    power=[7, 9],
                    is_valid=[True, False],
                )
            ],
        )

        changed_timesteps = [datetime(2020, 1, 1), datetime(2021, 1, 1), datetime(2022, 1, 1), datetime(2023, 1, 1)]
        periods = Periods.create_periods(
            times=changed_timesteps,
            include_before=False,
            include_after=False,
        )
        other_model = SimpleResultData(
            periods=periods,
            components=[
                SimpleComponentResult(
                    name="component1",
                    parent="installation1",
                    componentType=ComponentType.COMPRESSOR,
                    component_level=ComponentLevel.CONSUMER,
                    periods=periods,
                    emissions={
                        "co2": SimpleEmissionResult(
                            name="co2",
                            rate=[6, 8, 10],
                        )
                    },
                    energy_usage=[4, 6, 8],
                    energy_usage_unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                    power=[14, 16, 18],
                    is_valid=[True] * 3,
                )
            ],
        )
        other_model, reference_model, delta_profile, errors = SimpleResultData.delta_profile(
            reference_model,
            other_model,
        )
        timesteps = [datetime(2020, 1, 1), datetime(2021, 1, 1), datetime(2022, 1, 1), datetime(2023, 1, 1)]

        periods = Periods.create_periods(
            times=timesteps,
            include_before=False,
            include_after=False,
        )
        assert len(errors) == 0
        assert delta_profile == SimpleResultData(
            periods=periods,
            components=[
                SimpleComponentResult(
                    name="component1",
                    parent="installation1",
                    componentType=ComponentType.COMPRESSOR,
                    component_level=ComponentLevel.CONSUMER,
                    periods=periods,
                    emissions={
                        "co2": SimpleEmissionResult(
                            name="co2",
                            rate=[3, 5, 5],
                        )
                    },
                    energy_usage=[2, 4, 4],
                    energy_usage_unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                    power=[7, 9, 9],
                    is_valid=[True, True, False],
                ),
            ],
        )

    def test_different_periods_common_components_different_first_and_last_dates(self):
        """The model with the coarsest periods will be split to get values at the same places as the other model.
        Here the period covering 2020 - 2022 will be split in two equal models (2020-2021 and 2021-2022) for the
        reference model to match the periods in the changed model."""
        reference_timesteps = [datetime(2019, 1, 1), datetime(2022, 1, 1), datetime(2023, 1, 1)]
        periods = Periods.create_periods(
            times=reference_timesteps,
            include_before=False,
            include_after=False,
        )
        reference_model = SimpleResultData(
            periods=periods,
            components=[
                SimpleComponentResult(
                    name="component1",
                    parent="installation1",
                    componentType=ComponentType.COMPRESSOR,
                    component_level=ComponentLevel.CONSUMER,
                    periods=periods,
                    emissions={
                        "co2": SimpleEmissionResult(
                            name="co2",
                            rate=[3, 5],
                        )
                    },
                    energy_usage=[2, 4],
                    energy_usage_unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                    power=[7, 9],
                    is_valid=[True, False],
                )
            ],
        )

        changed_timesteps = [datetime(2020, 1, 1), datetime(2021, 1, 1), datetime(2022, 1, 1), datetime(2024, 1, 1)]
        periods = Periods.create_periods(
            times=changed_timesteps,
            include_before=False,
            include_after=False,
        )
        other_model = SimpleResultData(
            periods=periods,
            components=[
                SimpleComponentResult(
                    name="component1",
                    parent="installation1",
                    componentType=ComponentType.COMPRESSOR,
                    component_level=ComponentLevel.CONSUMER,
                    periods=periods,
                    emissions={
                        "co2": SimpleEmissionResult(
                            name="co2",
                            rate=[6, 8, 10],
                        )
                    },
                    energy_usage=[4, 6, 8],
                    energy_usage_unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                    power=[14, 16, 18],
                    is_valid=[True] * 3,
                )
            ],
        )
        other_model, reference_model, delta_profile, errors = SimpleResultData.delta_profile(
            reference_model,
            other_model,
        )
        timesteps = [datetime(2020, 1, 1), datetime(2021, 1, 1), datetime(2022, 1, 1), datetime(2023, 1, 1)]

        periods = Periods.create_periods(
            times=timesteps,
            include_before=False,
            include_after=False,
        )
        assert len(errors) == 0
        assert delta_profile == SimpleResultData(
            periods=periods,
            components=[
                SimpleComponentResult(
                    name="component1",
                    parent="installation1",
                    componentType=ComponentType.COMPRESSOR,
                    component_level=ComponentLevel.CONSUMER,
                    periods=periods,
                    emissions={
                        "co2": SimpleEmissionResult(
                            name="co2",
                            rate=[3, 5, 5],
                        )
                    },
                    energy_usage=[2, 4, 4],
                    energy_usage_unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                    power=[7, 9, 9],
                    is_valid=[True, True, False],
                ),
            ],
        )

    def test_different_emissions(self):
        periods = Periods.create_periods(
            times=[datetime(2020, 1, 1), datetime(2022, 1, 1), datetime(2023, 1, 1)],
            include_after=False,
            include_before=False,
        )
        reference_model = SimpleResultData(
            periods=periods,
            components=[
                SimpleComponentResult(
                    name="component1",
                    parent="installation1",
                    componentType=ComponentType.COMPRESSOR,
                    component_level=ComponentLevel.CONSUMER,
                    periods=periods,
                    emissions={
                        "co2": SimpleEmissionResult(
                            name="co2",
                            rate=[3, 5],
                        )
                    },
                    energy_usage=[0, 0],
                    energy_usage_unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                    power=[0, 0],
                    is_valid=[True, False],
                )
            ],
        )

        other_model = deepcopy(reference_model)
        other_model.components[0].emissions["methane"] = SimpleEmissionResult(
            name="methane",
            rate=[3, 5],
        )

        other_model, reference_model, delta_profile, errors = SimpleResultData.delta_profile(
            reference_model,
            other_model,
        )
        assert len(errors) == 0
        assert delta_profile == SimpleResultData(
            periods=periods,
            components=[
                SimpleComponentResult(
                    name="component1",
                    parent="installation1",
                    componentType=ComponentType.COMPRESSOR,
                    component_level=ComponentLevel.CONSUMER,
                    periods=periods,
                    emissions={
                        "co2": SimpleEmissionResult(
                            name="co2",
                            rate=[0, 0],
                        ),
                        "methane": SimpleEmissionResult(
                            name="methane",
                            rate=[3, 5],
                        ),
                    },
                    energy_usage=[0, 0],
                    energy_usage_unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                    power=[0, 0],
                    is_valid=[True, False],
                )
            ],
        )

    def test_optional_float(self):
        periods = Periods.create_periods(
            times=[datetime(2020, 1, 1), datetime(2021, 1, 1), datetime(2022, 1, 1), datetime(2023, 1, 1)],
            include_before=False,
            include_after=False,
        )
        reference_model = SimpleResultData(
            periods=periods,
            components=[
                SimpleComponentResult(
                    name="component1",
                    parent="installation1",
                    componentType=ComponentType.COMPRESSOR,
                    component_level=ComponentLevel.CONSUMER,
                    periods=periods,
                    emissions={
                        "co2": SimpleEmissionResult(
                            name="co2",
                            rate=[None, 4, 5],
                        )
                    },
                    energy_usage=[None, 3, 4],
                    energy_usage_unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                    power=[7, None, 9],
                    is_valid=[True] * len(periods),
                )
            ],
        )

        other_model = SimpleResultData(
            periods=periods,
            components=[
                SimpleComponentResult(
                    name="component1",
                    parent="installation1",
                    componentType=ComponentType.COMPRESSOR,
                    component_level=ComponentLevel.CONSUMER,
                    periods=periods,
                    emissions={
                        "co2": SimpleEmissionResult(
                            name="co2",
                            rate=[6, None, 10],
                        )
                    },
                    energy_usage=[4, None, 8],
                    energy_usage_unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                    power=[None, 16, 18],
                    is_valid=[True] * len(periods),
                )
            ],
        )

        other_model, reference_model, delta_profile, errors = SimpleResultData.delta_profile(
            reference_model,
            other_model,
        )
        assert len(errors) == 0
        assert delta_profile == SimpleResultData(
            periods=periods,
            components=[
                SimpleComponentResult(
                    name="component1",
                    parent="installation1",
                    componentType=ComponentType.COMPRESSOR,
                    component_level=ComponentLevel.CONSUMER,
                    periods=periods,
                    emissions={
                        "co2": SimpleEmissionResult(
                            name="co2",
                            rate=[6, -4, 5],
                        )
                    },
                    energy_usage=[4, -3, 4],
                    energy_usage_unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                    power=[-7, 16, 9],
                    is_valid=[True] * len(periods),
                )
            ],
        )

    def test_same_model(self):
        periods = Periods.create_periods(
            times=[datetime(2020, 1, 1), datetime(2021, 1, 1), datetime(2022, 1, 1), datetime(2023, 1, 1)],
            include_before=False,
            include_after=False,
        )
        model = SimpleResultData(
            periods=periods,
            components=[
                SimpleComponentResult(
                    name="component1",
                    parent="installation1",
                    componentType=ComponentType.COMPRESSOR,
                    component_level=ComponentLevel.CONSUMER,
                    periods=periods,
                    emissions={
                        "co2": SimpleEmissionResult(
                            name="co2",
                            rate=[3, 4, 5],
                        )
                    },
                    energy_usage=[2, 3, 4],
                    energy_usage_unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                    power=[7, 8, 9],
                    is_valid=[True] * len(periods),
                )
            ],
        )

        other_model, reference_model, delta_profile, errors = SimpleResultData.delta_profile(
            model,
            model,
        )
        assert len(errors) == 0
        assert delta_profile == SimpleResultData(
            periods=periods,
            components=[
                SimpleComponentResult(
                    name="component1",
                    parent="installation1",
                    componentType=ComponentType.COMPRESSOR,
                    component_level=ComponentLevel.CONSUMER,
                    periods=periods,
                    emissions={
                        "co2": SimpleEmissionResult(
                            name="co2",
                            rate=[0, 0, 0],
                        )
                    },
                    energy_usage=[0, 0, 0],
                    energy_usage_unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                    power=[0, 0, 0],
                    is_valid=[True] * len(periods),
                )
            ],
        )
