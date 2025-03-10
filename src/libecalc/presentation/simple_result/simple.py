from typing import NamedTuple, Optional

from pydantic import BaseModel, ConfigDict, model_validator

from libecalc.common.component_info.component_level import ComponentLevel
from libecalc.common.component_type import ComponentType
from libecalc.common.logger import logger
from libecalc.common.string.string_utils import to_camel_case
from libecalc.common.time_utils import Period, Periods
from libecalc.common.units import Unit
from libecalc.presentation.json_result.result import ComponentResult, EcalcModelResult

opt_float = Optional[float]


class SimpleBase(BaseModel):
    model_config = ConfigDict(
        extra="ignore",
        alias_generator=to_camel_case,
        populate_by_name=True,
    )


class SimpleEmissionResult(SimpleBase):
    name: str
    rate: list[opt_float]

    @model_validator(mode="before")
    def convert_time_series(cls, values):
        rate = values.get("rate")

        if isinstance(rate, dict):
            # Parsing DTO result to simple
            values["rate"] = rate["values"]

        return values

    def __sub__(self, reference_emission) -> "SimpleEmissionResult":
        """Calculate difference between two emission results."""
        if not isinstance(reference_emission, SimpleEmissionResult):
            raise TypeError(
                f"unsupported operand type(s) for -: '{type(self).__name__}' and '{type(reference_emission).__name__}'"
            )
        if self.name != reference_emission.name:
            raise ValueError(f"Can not subtract different emissions: '{self.name}' and '{reference_emission.name}'")
        return SimpleEmissionResult(
            name=self.name,
            rate=_subtract_list(self.rate, reference_emission.rate),
        )


class ComponentID(NamedTuple):
    componentType: ComponentType
    name: str

    def __repr__(self):
        return f"(type: '{self.componentType}', name: '{self.name}')"


def _subtract_list(first: list[float | None], second: list[float | None]):
    subtracted = []
    for f, s in zip(first, second):
        if f is None:
            f = 0
        if s is None:
            s = 0
        subtracted.append(f - s)

    return subtracted


class SimpleComponentResult(SimpleBase):
    componentType: ComponentType
    component_level: ComponentLevel
    parent: str | None = None
    name: str
    periods: Periods
    is_valid: list[int]
    emissions: dict[str, SimpleEmissionResult]

    energy_usage: list[opt_float]
    energy_usage_unit: Unit
    power: list[opt_float] | None = None

    @classmethod
    def from_dto(cls, component_result: ComponentResult) -> "SimpleComponentResult":
        return SimpleComponentResult(**component_result.model_dump())

    @model_validator(mode="before")
    @classmethod
    def convert_time_series(cls, values):
        energy_usage = values.get("energy_usage")
        is_valid = values.get("is_valid")
        power = values.get("power")

        if isinstance(energy_usage, dict):
            # Parsing DTO result to simple
            values["energy_usage"] = energy_usage["values"]
            values["energy_usage_unit"] = energy_usage["unit"]

        if isinstance(is_valid, dict):
            # Parsing DTO result to simple
            values["is_valid"] = is_valid["values"]

        if power is not None:
            if isinstance(power, dict):
                values["power"] = power["values"]
        else:
            values["power"] = None

        return values

    @property
    def id(self) -> ComponentID:
        return ComponentID(componentType=self.componentType, name=self.name)

    @classmethod
    def fit_to_periods(
        cls,
        component: "SimpleComponentResult",
        periods: Periods,
    ) -> "SimpleComponentResult":
        """Fits the component to the given periods.

        * The given periods needs to cover at least the same time span as the original periods.
        * If a given period extends beyond the first and last dates in the original periods,
            it will be cut/forced to cover the same time span as the original periods.
        * After being constrained to the original periods, the given periods should contain all dates
            in the original periods (and likely some more). This means that some of the original periods
            will be split into multiple periods - each with the same energy usage, power, etc. - to make
            delta profile comparisons easier/possible.

        Args:
            component (SimpleComponentResult): The component that should be fitted (should intersect all periods in the periods list). Can have periods before and after the *periods*. Those will be trimmed.
            periods (Periods): The target periods. The provided periods should all exist in the component. If the above component are missing periods, we will extrapolate with values from the bigger period

        Returns:
            SimpleComponentResult: The component with the new periods, ie. start and end will be trimmed, and mid-periods will be added if the component has a longer period than the global period.
        """
        power = []
        energy_usage = []
        is_valid = []
        emissions: dict[str, SimpleEmissionResult] = {
            emission.name: SimpleEmissionResult(name=emission.name, rate=[])
            for emission in component.emissions.values()
        }
        # We loop through a components periods and try to fit it to the common global period.
        for period_index, _period in enumerate(component.periods):
            period = Period.intersection(_period, periods.period)
            # If the period is not in the global period, we skip it. ie before or after the global common period.
            if period:
                start = periods.start_dates.index(period.start)
                end = periods.end_dates.index(period.end)

                # In case we have a longer period in component than the global period, we have to add missing steps/periods
                # e.g. if the common period has 2022-2023, but the component has 2022-2024, we have to loop twice to extrapolate the missing period with same values as the bigger period.
                # Usually this will only loop once.
                for _ in range(start, end + 1):
                    if component.power is not None:
                        power.append(component.power[period_index])
                    energy_usage.append(component.energy_usage[period_index])
                    is_valid.append(component.is_valid[period_index])
                    for emission in emissions.values():
                        # Assume index exist if emission exist
                        emission.rate.append(component.emissions[emission.name].rate[period_index])
            else:
                # We do not trim extraneous periods in beginning and end for a component. We only try to fit to the common global period.
                logger.warning(
                    f"Period {component.periods[period_index]} from {component.name} not in {periods.period}. Skipping."
                )

        return cls(
            componentType=component.componentType,
            component_level=component.component_level,
            parent=component.parent,
            name=component.name,
            power=power,
            energy_usage=energy_usage,
            energy_usage_unit=component.energy_usage_unit,
            emissions=emissions,
            is_valid=is_valid,
            periods=periods,
        )

    def __sub__(self, reference_component) -> "SimpleComponentResult":
        """Calculate difference between two component results."""
        if not isinstance(reference_component, SimpleComponentResult):
            raise TypeError(
                f"unsupported operand type(s) for -: '{type(self).__name__}' and '{type(reference_component).__name__}'"
            )
        if self.id != reference_component.id:
            raise ValueError(
                f"Can not compare different components, id does not match: {self.id} and {reference_component.id}"
            )
        if self.periods != reference_component.periods:
            raise ValueError(
                f"Can not compare components with differing periods: {self.id} and {reference_component.id}"
            )
        if self.energy_usage_unit != reference_component.energy_usage_unit:
            raise ValueError(
                f"Can not compare components with differing energy usage units: "
                f"{self.id} with unit '{self.energy_usage_unit}' and "
                f"{reference_component.id} with unit '{reference_component.energy_usage_unit}'."
            )

        return SimpleComponentResult(
            name=self.name,
            parent=self.parent if self.parent == reference_component.parent else None,
            componentType=self.componentType,
            component_level=self.component_level,
            periods=self.periods,
            is_valid=[changed and reference for changed, reference in zip(self.is_valid, reference_component.is_valid)],
            energy_usage=_subtract_list(self.energy_usage, reference_component.energy_usage),
            energy_usage_unit=self.energy_usage_unit,
            power=_subtract_list(self.power, reference_component.power),  # type: ignore[arg-type]
            emissions={
                self_e.name: self_e - reference_e
                for self_e, reference_e in zip(
                    sorted(self.emissions.values(), key=lambda emission: emission.name),
                    sorted(reference_component.emissions.values(), key=lambda emission: emission.name),
                )
            },
        )


def _create_empty_component(component: SimpleComponentResult) -> SimpleComponentResult:
    return SimpleComponentResult(
        componentType=component.componentType,
        component_level=component.component_level,
        name=component.name,
        parent=component.parent,
        periods=component.periods,
        energy_usage=[0] * len(component.periods),
        energy_usage_unit=component.energy_usage_unit,
        power=[0] * len(component.periods),
        emissions={
            emission.name: SimpleEmissionResult(
                name=emission.name,
                rate=[0] * len(component.periods),
            )
            for emission in component.emissions.values()
        },
        is_valid=[True] * len(component.periods),
    )


class SimpleResultData(SimpleBase):
    periods: Periods
    components: list[SimpleComponentResult]

    @classmethod
    def from_dto(cls, result: EcalcModelResult) -> "SimpleResultData":
        return SimpleResultData(
            periods=result.periods,
            components=[SimpleComponentResult.from_dto(component) for component in result.components],
        )

    @classmethod
    def fit_to_periods(
        cls,
        model: "SimpleResultData",
        periods: Periods,
    ) -> "SimpleResultData":
        """
        Fit result to periods. Only a subset or the same set of periods is supported.
        Args:
            model:
            periods:

        Returns:

        """
        return cls(
            periods=periods,
            components=[
                SimpleComponentResult.fit_to_periods(component=component, periods=periods)
                for component in model.components
            ],
        )

    @classmethod
    def subtract(
        cls,
        changed_model: "SimpleResultData",
        reference_model: "SimpleResultData",
    ) -> tuple["SimpleResultData", list[Exception]]:
        """Subtract reference model from changed model.

        Timesteps and components should be equal between the models.
        """
        if changed_model.periods != reference_model.periods:
            raise ValueError(
                "Timesteps should be equal between models when calculating delta profile. "
                "Use separate methods to normalize."
            )
        periods = reference_model.periods

        errors = []
        components = []
        for changed_component, reference_component in zip(changed_model.components, reference_model.components):
            try:
                components.append(changed_component - reference_component)
            except ValueError as e:
                logger.error(e)
                errors.append(e)

        return SimpleResultData(periods=periods, components=components), errors

    @classmethod
    def _normalize_emissions(cls, changed_component, reference_component):
        emission_names = set(changed_component.emissions.keys()).union(x for x in reference_component.emissions)

        for emission_name in emission_names:
            for component in [changed_component, reference_component]:
                if emission_name not in list(component.emissions):
                    vector_length = len(component.periods)
                    component.emissions[emission_name] = SimpleEmissionResult(
                        name=emission_name,
                        rate=[0] * vector_length,
                    )

        return changed_component, reference_component

    @classmethod
    def normalize_components(
        cls,
        reference_model: "SimpleResultData",
        changed_model: "SimpleResultData",
        exclude: list[ComponentType] | None = None,
    ) -> tuple["SimpleResultData", "SimpleResultData"]:
        if exclude is None:
            exclude = []

        changed_components = {component.id: component for component in changed_model.components}
        reference_components = {component.id: component for component in reference_model.components}

        component_ids = sorted(set(changed_components.keys()).union(set(reference_components.keys())))

        filtered_component_ids = [
            component_id for component_id in component_ids if component_id.componentType not in exclude
        ]

        normalized_reference_components = []
        normalized_changed_components = []

        for component_id in filtered_component_ids:
            changed_component = changed_components.get(component_id)
            reference_component = reference_components.get(component_id)

            if changed_component is None and reference_component is not None:
                changed_component = _create_empty_component(reference_component)
            elif reference_component is None and changed_component is not None:
                reference_component = _create_empty_component(changed_component)

            changed_component, reference_component = cls._normalize_emissions(
                reference_component=reference_component, changed_component=changed_component
            )

            normalized_reference_components.append(reference_component)
            normalized_changed_components.append(changed_component)

        return (
            cls(periods=changed_model.periods, components=normalized_changed_components),
            cls(periods=reference_model.periods, components=normalized_reference_components),
        )

    @classmethod
    def delta_profile(
        cls,
        reference_model: "SimpleResultData",
        changed_model: "SimpleResultData",
    ) -> tuple["SimpleResultData", "SimpleResultData", "SimpleResultData", list[str]]:
        """
        Calculate delta profile between two models. We will make sure that both models have the same
        periods and components before calculating the delta profile. Different start and end will be trimmed.
        This delta-profile methods supports both periods with fixed interval (monthly, yearly) and irregular intervals (data-defined).
        The resulting delta-profile will have the union of the periods from both models, except differing start and end, that will be trimmed,
        in order to have same start and end for both models.

        Args:
            reference_model:
            changed_model:

        Returns:

        """
        # find all dates in both models for the period both models are defined
        first_date = max(changed_model.periods.first_date, reference_model.periods.first_date)
        last_date = min(changed_model.periods.last_date, reference_model.periods.last_date)

        # union of the dates in the 2 models
        all_dates_in_models = sorted(
            {date for date in reference_model.periods.all_dates if first_date <= date <= last_date}.union(
                {date for date in changed_model.periods.all_dates if first_date <= date <= last_date}
            )
        )

        # define new periods using all dates in both models, skip extra periods before and after
        periods = Periods.create_periods(
            times=all_dates_in_models,
            include_after=False,
            include_before=False,
        )

        # Normalize components first as we need to filter out CONSUMER_MODELs for normalize_timesteps to work.
        changed_model, reference_model = cls.normalize_components(
            reference_model=reference_model, changed_model=changed_model
        )

        # Now as we have found the union of the dates/periods in the models, and trimming
        # start end, if they differ, we can fill out missing periods for the models
        changed_model = cls.fit_to_periods(changed_model, periods)
        reference_model = cls.fit_to_periods(reference_model, periods)

        delta_profile, errors = cls.subtract(changed_model=changed_model, reference_model=reference_model)

        return changed_model, reference_model, delta_profile, [str(error) for error in errors]
