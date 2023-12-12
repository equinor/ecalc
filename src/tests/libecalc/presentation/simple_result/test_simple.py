from copy import deepcopy
from datetime import datetime

from libecalc.common.component_info.component_level import ComponentLevel
from libecalc.common.units import Unit
from libecalc.dto.base import ComponentType
from libecalc.presentation.simple_result.simple import (
    SimpleComponentResult,
    SimpleEmissionResult,
    SimpleResultData,
)


class TestDeltaProfile:
    def test_common_timesteps_common_components(self):
        timesteps = [datetime(2020, 1, 1), datetime(2021, 1, 1), datetime(2022, 1, 1)]
        reference_model = SimpleResultData(
            timesteps=timesteps,
            components=[
                SimpleComponentResult(
                    name="component1",
                    parent="installation1",
                    componentType=ComponentType.COMPRESSOR,
                    component_level=ComponentLevel.CONSUMER,
                    timesteps=timesteps,
                    emissions={
                        "co2": SimpleEmissionResult(
                            name="co2",
                            rate=[3, 4, 5],
                        )
                    },
                    energy_usage=[2, 3, 4],
                    energy_usage_unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                    power=[7, 8, 9],
                    is_valid=[True] * len(timesteps),
                )
            ],
        )

        other_model = SimpleResultData(
            timesteps=timesteps,
            components=[
                SimpleComponentResult(
                    name="component1",
                    parent="installation1",
                    componentType=ComponentType.COMPRESSOR,
                    component_level=ComponentLevel.CONSUMER,
                    timesteps=timesteps,
                    emissions={
                        "co2": SimpleEmissionResult(
                            name="co2",
                            rate=[6, 8, 10],
                        )
                    },
                    energy_usage=[4, 6, 8],
                    energy_usage_unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                    power=[14, 16, 18],
                    is_valid=[True] * len(timesteps),
                )
            ],
        )
        other_model, reference_model, delta_profile, errors = SimpleResultData.delta_profile(
            other_model, reference_model
        )
        assert delta_profile == reference_model
        assert len(errors) == 0

    def test_common_timesteps_different_components(self):
        """Test that missing components is treated as zero,
        i.e. missing_component - reference_component = -1 * reference_component and
             changed_component - missing_component = changed_component.
        """
        timesteps = [datetime(2020, 1, 1), datetime(2021, 1, 1), datetime(2022, 1, 1)]
        reference_model = SimpleResultData(
            timesteps=timesteps,
            components=[
                SimpleComponentResult(
                    name="component1",
                    parent="installation1",
                    componentType=ComponentType.COMPRESSOR,
                    component_level=ComponentLevel.CONSUMER,
                    timesteps=timesteps,
                    emissions={
                        "co2": SimpleEmissionResult(
                            name="co2",
                            rate=[3, 4, 5],
                        )
                    },
                    energy_usage=[2, 3, 4],
                    energy_usage_unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                    power=[7, 8, 9],
                    is_valid=[True] * len(timesteps),
                )
            ],
        )

        component_2 = SimpleComponentResult(
            name="component2",
            parent="installation1",
            componentType=ComponentType.COMPRESSOR,
            component_level=ComponentLevel.CONSUMER,
            timesteps=timesteps,
            emissions={
                "co2": SimpleEmissionResult(
                    name="co2",
                    rate=[6, 8, 10],
                )
            },
            energy_usage=[4, 6, 8],
            energy_usage_unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
            power=[14, 16, 18],
            is_valid=[True] * len(timesteps),
        )

        other_model = SimpleResultData(timesteps=timesteps, components=[component_2])
        other_model, reference_model, delta_profile, errors = SimpleResultData.delta_profile(
            other_model, reference_model
        )
        assert len(errors) == 0
        assert delta_profile == SimpleResultData(
            timesteps=timesteps,
            components=[
                SimpleComponentResult(
                    name="component1",
                    parent="installation1",
                    componentType=ComponentType.COMPRESSOR,
                    component_level=ComponentLevel.CONSUMER,
                    timesteps=timesteps,
                    emissions={
                        "co2": SimpleEmissionResult(
                            name="co2",
                            rate=[-3, -4, -5],
                        )
                    },
                    energy_usage=[-2, -3, -4],
                    energy_usage_unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                    power=[-7, -8, -9],
                    is_valid=[True] * len(timesteps),
                ),
                component_2,
            ],
        )

    def test_different_timesteps_common_components(self):
        """Test that missing timesteps will be skipped."""
        reference_timesteps = [datetime(2020, 1, 1), datetime(2022, 1, 1)]
        reference_model = SimpleResultData(
            timesteps=reference_timesteps,
            components=[
                SimpleComponentResult(
                    name="component1",
                    parent="installation1",
                    componentType=ComponentType.COMPRESSOR,
                    component_level=ComponentLevel.CONSUMER,
                    timesteps=reference_timesteps,
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

        changed_timesteps = [datetime(2020, 1, 1), datetime(2021, 1, 1), datetime(2022, 1, 1)]

        other_model = SimpleResultData(
            timesteps=changed_timesteps,
            components=[
                SimpleComponentResult(
                    name="component1",
                    parent="installation1",
                    componentType=ComponentType.COMPRESSOR,
                    component_level=ComponentLevel.CONSUMER,
                    timesteps=changed_timesteps,
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

        timesteps = [datetime(2020, 1, 1), datetime(2022, 1, 1)]

        other_model, reference_model, delta_profile, errors = SimpleResultData.delta_profile(
            other_model, reference_model
        )
        assert len(errors) == 0
        assert delta_profile == SimpleResultData(
            timesteps=timesteps,
            components=[
                SimpleComponentResult(
                    name="component1",
                    parent="installation1",
                    componentType=ComponentType.COMPRESSOR,
                    component_level=ComponentLevel.CONSUMER,
                    timesteps=timesteps,
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
                ),
            ],
        )

    def test_different_emissions(self):
        reference_timesteps = [datetime(2020, 1, 1), datetime(2022, 1, 1)]
        reference_model = SimpleResultData(
            timesteps=reference_timesteps,
            components=[
                SimpleComponentResult(
                    name="component1",
                    parent="installation1",
                    componentType=ComponentType.COMPRESSOR,
                    component_level=ComponentLevel.CONSUMER,
                    timesteps=reference_timesteps,
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
            other_model, reference_model
        )
        assert len(errors) == 0
        assert delta_profile == SimpleResultData(
            timesteps=reference_timesteps,
            components=[
                SimpleComponentResult(
                    name="component1",
                    parent="installation1",
                    componentType=ComponentType.COMPRESSOR,
                    component_level=ComponentLevel.CONSUMER,
                    timesteps=reference_timesteps,
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
        timesteps = [datetime(2020, 1, 1), datetime(2021, 1, 1), datetime(2022, 1, 1)]
        reference_model = SimpleResultData(
            timesteps=timesteps,
            components=[
                SimpleComponentResult(
                    name="component1",
                    parent="installation1",
                    componentType=ComponentType.COMPRESSOR,
                    component_level=ComponentLevel.CONSUMER,
                    timesteps=timesteps,
                    emissions={
                        "co2": SimpleEmissionResult(
                            name="co2",
                            rate=[None, 4, 5],
                        )
                    },
                    energy_usage=[None, 3, 4],
                    energy_usage_unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                    power=[7, None, 9],
                    is_valid=[True] * len(timesteps),
                )
            ],
        )

        other_model = SimpleResultData(
            timesteps=timesteps,
            components=[
                SimpleComponentResult(
                    name="component1",
                    parent="installation1",
                    componentType=ComponentType.COMPRESSOR,
                    component_level=ComponentLevel.CONSUMER,
                    timesteps=timesteps,
                    emissions={
                        "co2": SimpleEmissionResult(
                            name="co2",
                            rate=[6, None, 10],
                        )
                    },
                    energy_usage=[4, None, 8],
                    energy_usage_unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                    power=[None, 16, 18],
                    is_valid=[True] * len(timesteps),
                )
            ],
        )

        other_model, reference_model, delta_profile, errors = SimpleResultData.delta_profile(
            other_model, reference_model
        )
        assert len(errors) == 0
        assert delta_profile == SimpleResultData(
            timesteps=timesteps,
            components=[
                SimpleComponentResult(
                    name="component1",
                    parent="installation1",
                    componentType=ComponentType.COMPRESSOR,
                    component_level=ComponentLevel.CONSUMER,
                    timesteps=timesteps,
                    emissions={
                        "co2": SimpleEmissionResult(
                            name="co2",
                            rate=[6, -4, 5],
                        )
                    },
                    energy_usage=[4, -3, 4],
                    energy_usage_unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                    power=[-7, 16, 9],
                    is_valid=[True] * len(timesteps),
                )
            ],
        )

    def test_same_model(self):
        timesteps = [datetime(2020, 1, 1), datetime(2021, 1, 1), datetime(2022, 1, 1)]
        model = SimpleResultData(
            timesteps=timesteps,
            components=[
                SimpleComponentResult(
                    name="component1",
                    parent="installation1",
                    componentType=ComponentType.COMPRESSOR,
                    component_level=ComponentLevel.CONSUMER,
                    timesteps=timesteps,
                    emissions={
                        "co2": SimpleEmissionResult(
                            name="co2",
                            rate=[3, 4, 5],
                        )
                    },
                    energy_usage=[2, 3, 4],
                    energy_usage_unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                    power=[7, 8, 9],
                    is_valid=[True] * len(timesteps),
                )
            ],
        )

        other_model, reference_model, delta_profile, errors = SimpleResultData.delta_profile(
            model,
            model,
        )
        assert len(errors) == 0
        assert delta_profile == SimpleResultData(
            timesteps=timesteps,
            components=[
                SimpleComponentResult(
                    name="component1",
                    parent="installation1",
                    componentType=ComponentType.COMPRESSOR,
                    component_level=ComponentLevel.CONSUMER,
                    timesteps=timesteps,
                    emissions={
                        "co2": SimpleEmissionResult(
                            name="co2",
                            rate=[0, 0, 0],
                        )
                    },
                    energy_usage=[0, 0, 0],
                    energy_usage_unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                    power=[0, 0, 0],
                    is_valid=[True] * len(timesteps),
                )
            ],
        )
