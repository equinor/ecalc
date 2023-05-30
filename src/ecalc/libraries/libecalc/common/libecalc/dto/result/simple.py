import enum
from datetime import datetime
from typing import Dict, List, NamedTuple, Optional, Tuple

from libecalc.common.component_info.component_level import ComponentLevel
from libecalc.common.logger import logger
from libecalc.common.units import Unit
from libecalc.dto.base import ComponentType
from libecalc.dto.result.base import EcalcResultBaseModel
from libecalc.dto.result.types import opt_float
from pydantic import Extra, root_validator
from scipy.interpolate import interp1d


class SimpleBase(EcalcResultBaseModel):
    class Config:
        extra = Extra.ignore

    def dict(self, exclude_none=True, **kwargs):
        return super().dict(exclude_none=exclude_none, **kwargs)

    def json(self, **kwargs):
        return super().json(**kwargs)


class SimpleEmissionResult(SimpleBase):
    name: str
    rate: List[opt_float]

    @root_validator(pre=True)
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


def _subtract_list(first: List[Optional[float]], second: List[Optional[float]]):
    subtracted = []
    for f, s in zip(first, second):
        if f is None:
            f = 0
        if s is None:
            s = 0
        subtracted.append(f - s)

    return subtracted


class InterpolationMethod(str, enum.Enum):
    SKIP = "SKIP"
    LINEAR = "LINEAR"
    # FILL_ZERO can be handled by scipy, same as linear. kind='zero' if needed.


interpolationKindMap = {
    InterpolationMethod.LINEAR: "linear",
}


def _interpolate_list(
    x: List[datetime],
    y: List[float],
    target_x: List[datetime],
    method: InterpolationMethod,
) -> List[float]:
    if len(y) != len(x):
        raise ValueError("x and y should have equal length.")

    if len(y) == 0:
        return []

    if len(y) == 1:
        return [y[0]] * len(target_x)

    if x == target_x:
        return y

    if len(target_x) == 0:
        return []

    kind = interpolationKindMap[method]
    start = min(x[0], target_x[0])
    x_in_seconds = [(time_step - start).total_seconds() for time_step in x]
    target_x_in_seconds = [(time_step - start).total_seconds() for time_step in target_x]

    return list(
        interp1d(
            x=x_in_seconds,
            y=y,
            fill_value=(y[0], y[-1]),
            assume_sorted=True,
            kind=kind,
        )(target_x_in_seconds)
    )


class SimpleComponentResult(SimpleBase):
    componentType: ComponentType
    component_level: ComponentLevel
    parent: Optional[str]
    name: str
    timesteps: List[datetime]
    is_valid: List[int]
    emissions: Dict[str, SimpleEmissionResult]

    energy_usage: List[opt_float]
    energy_usage_unit: Unit
    power: Optional[List[opt_float]]

    @root_validator(pre=True)
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
    def fit_to_timesteps(
        cls,
        component: "SimpleComponentResult",
        timesteps: List[datetime],
        method: InterpolationMethod = InterpolationMethod.SKIP,
    ) -> "SimpleComponentResult":
        """Fit the component to the provided timesteps based on specified method.

        :param component: The component that should be normalized
        :param timesteps: the target timesteps. These should already be correct based on the InterpolationMethod
            specified, i.e. if InterpolationMethod is SKIP, the provided timesteps should all exist in the component.
        :param method: The interpolation method that should be used to fill values
        :return: the normalized component
        """
        if method == InterpolationMethod.SKIP:
            power = []
            energy_usage = []
            is_valid = []
            emissions: Dict[str, SimpleEmissionResult] = {
                emission.name: SimpleEmissionResult(name=emission.name, rate=[])
                for emission in component.emissions.values()
            }
            for timestep in timesteps:
                if timestep in component.timesteps:
                    timestep_index = component.timesteps.index(timestep)

                    if component.power is not None:
                        power.append(component.power[timestep_index])

                    energy_usage.append(component.energy_usage[timestep_index])

                    is_valid.append(component.is_valid[timestep_index])
                    for emission in emissions.values():
                        # Assume index exist if emission exist
                        emission.rate.append(component.emissions[emission.name].rate[timestep_index])
                else:
                    # This is a developer error, we should provide the correct timesteps.
                    raise ValueError(
                        f"Provided timesteps includes timestep not found in component {component.id}. "
                        f"Extraneous timestep: {timestep}. This should not happen, contact support."
                    )
        elif method == InterpolationMethod.LINEAR:
            emissions = {
                emission.name: SimpleEmissionResult(
                    name=emission.name,
                    rate=_interpolate_list(
                        x=component.timesteps,
                        y=emission.rate,
                        target_x=timesteps,
                        method=method,
                    ),
                )
                for emission in component.emissions.values()
            }

            is_valid = []
            for timestep in timesteps:
                if timestep in component.timesteps:
                    timestep_index = component.timesteps.index(timestep)
                    is_valid.append(component.is_valid[timestep_index])
                else:
                    is_valid.append(True)

            power = None
            if component.power is not None:
                power = _interpolate_list(
                    x=component.timesteps,
                    y=component.power,
                    target_x=timesteps,
                    method=method,
                )

            energy_usage = _interpolate_list(
                x=component.timesteps,
                y=component.energy_usage,
                target_x=timesteps,
                method=method,
            )
        else:
            raise NotImplementedError()

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
            timesteps=timesteps,
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
        if self.timesteps != reference_component.timesteps:
            raise ValueError(
                f"Can not compare components with differing timesteps: {self.id} and {reference_component.id}"
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
            timesteps=self.timesteps,
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
        timesteps=component.timesteps,
        energy_usage=[0] * len(component.timesteps),
        energy_usage_unit=component.energy_usage_unit,
        power=[0] * len(component.timesteps),
        emissions={
            emission.name: SimpleEmissionResult(
                name=emission.name,
                rate=[0] * len(component.timesteps),
            )
            for emission in component.emissions.values()
        },
        is_valid=[True] * len(component.timesteps),
    )


class SimpleResultData(SimpleBase):
    timesteps: List[datetime]
    components: List[SimpleComponentResult]

    @classmethod
    def fit_to_timesteps(
        cls,
        model: "SimpleResultData",
        timesteps: List[datetime],
        method: InterpolationMethod = InterpolationMethod.SKIP,
    ):
        return cls(
            timesteps=timesteps,
            components=[
                SimpleComponentResult.fit_to_timesteps(component=component, timesteps=timesteps, method=method)
                for component in model.components
            ],
        )

    @classmethod
    def subtract(
        cls,
        other_model: "SimpleResultData",
        reference_model: "SimpleResultData",
    ) -> Tuple["SimpleResultData", List[Exception]]:
        """Subtract reference model from other model.

        Timesteps and components should be equal between the models.
        """
        if other_model.timesteps != reference_model.timesteps:
            raise ValueError(
                "Timesteps should be equal between models when calculating delta profile. "
                "Use separate methods to normalize."
            )
        timesteps = reference_model.timesteps

        errors = []
        components = []
        for other_component, reference_component in zip(other_model.components, reference_model.components):
            try:
                components.append(other_component - reference_component)
            except ValueError as e:
                logger.error(e)
                errors.append(e)

        return SimpleResultData(timesteps=timesteps, components=components), errors

    @classmethod
    def _normalize_emissions(cls, other_component, reference_component):
        emission_names = set(other_component.emissions.keys()).union(x for x in reference_component.emissions)

        for emission_name in emission_names:
            for component in [other_component, reference_component]:
                if emission_name not in list(component.emissions):
                    vector_length = len(component.timesteps)
                    component.emissions[emission_name] = SimpleEmissionResult(
                        name=emission_name,
                        rate=[0] * vector_length,
                    )

        return other_component, reference_component

    @classmethod
    def normalize_components(
        cls,
        other_model: "SimpleResultData",
        reference_model: "SimpleResultData",
        exclude: Optional[List[ComponentType]] = None,
    ):
        if exclude is None:
            exclude = []

        other_components = {component.id: component for component in other_model.components}
        reference_components = {component.id: component for component in reference_model.components}

        component_ids = sorted(set(other_components.keys()).union(set(reference_components.keys())))

        filtered_component_ids = [
            component_id for component_id in component_ids if component_id.componentType not in exclude
        ]

        normalized_reference_components = []
        normalized_other_components = []

        for component_id in filtered_component_ids:
            other_component = other_components.get(component_id)
            reference_component = reference_components.get(component_id)

            if other_component is None and reference_component is not None:
                other_component = _create_empty_component(reference_component)
            elif reference_component is None and other_component is not None:
                reference_component = _create_empty_component(other_component)

            other_component, reference_component = cls._normalize_emissions(other_component, reference_component)

            normalized_reference_components.append(reference_component)
            normalized_other_components.append(other_component)

        return (
            cls(timesteps=other_model.timesteps, components=normalized_other_components),
            cls(timesteps=reference_model.timesteps, components=normalized_reference_components),
        )

    @classmethod
    def delta_profile(
        cls,
        other_model: "SimpleResultData",
        reference_model: "SimpleResultData",
        interpolation_method: InterpolationMethod = InterpolationMethod.SKIP,
    ) -> Tuple["SimpleResultData", "SimpleResultData", "SimpleResultData", List[str]]:
        if interpolation_method == InterpolationMethod.SKIP:
            timesteps = sorted(set(other_model.timesteps).intersection(reference_model.timesteps))
        elif interpolation_method == InterpolationMethod.LINEAR:
            timesteps = sorted(set(other_model.timesteps).union(reference_model.timesteps))
        else:
            raise NotImplementedError

        # Normalize components first as we need to filter out CONSUMER_MODELs for normalize_timesteps to work.
        other_model, reference_model = cls.normalize_components(other_model, reference_model)

        other_model = cls.fit_to_timesteps(other_model, timesteps, method=interpolation_method)
        reference_model = cls.fit_to_timesteps(reference_model, timesteps, method=interpolation_method)

        delta_profile, errors = cls.subtract(other_model, reference_model)

        return other_model, reference_model, delta_profile, [str(error) for error in errors]
