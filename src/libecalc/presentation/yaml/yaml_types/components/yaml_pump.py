from datetime import datetime
from typing import Dict, List, Literal, Optional

from pydantic import Field

from libecalc import dto
from libecalc.common.string.string_utils import generate_id
from libecalc.common.temporal_model import TemporalModel
from libecalc.common.time_utils import Period, define_time_model_for_period
from libecalc.core.consumers.pump import Pump
from libecalc.core.models.pump import create_pump_model
from libecalc.domain.stream_conditions import Density, Pressure, Rate, StreamConditions
from libecalc.dto import PumpModel, VariablesMap
from libecalc.dto.base import ComponentType
from libecalc.dto.components import PumpComponent
from libecalc.dto.types import ConsumptionType
from libecalc.expression import Expression
from libecalc.presentation.yaml.mappers.utils import resolve_reference
from libecalc.presentation.yaml.yaml_entities import References
from libecalc.presentation.yaml.yaml_types.components.yaml_base import (
    YamlConsumerBase,
)
from libecalc.presentation.yaml.yaml_types.yaml_temporal_model import YamlTemporalModel


class YamlPump(YamlConsumerBase):
    """
    This is a DTO, a yaml DTO
    """

    class Config:
        title = "Pump"

    component_type: Literal[ComponentType.PUMP_V2] = Field(
        ...,
        title="TYPE",
        description="The type of the component",
        alias="TYPE",
    )

    energy_usage_model: YamlTemporalModel[str]

    # TODO: Same for compressor and pump and ...?
    # stream_conditions: Optional[YamlConsumerStreamConditions]  # TODO: use NAME instead of Dict[StreamID, YamlStreamConditions] TODO: optional...since it may be set as a part of consumer system and overridden/set runtime?

    def to_dto(
        self,
        consumes: ConsumptionType,
        regularity: Dict[datetime, Expression],
        target_period: Period,
        references: References,
        category: str,
        fuel: Optional[Dict[datetime, dto.types.FuelType]],
    ) -> PumpComponent:
        """
        We are deprecating to_dto, and aim to remove the DTO layer and go directly to a user and dev friendly
        domain layer (API)

        Args:
            consumes:
            regularity:
            target_period:
            references:
            category:
            fuel:

        Returns:

        """
        return PumpComponent(
            consumes=consumes,
            regularity=regularity,
            name=self.name,
            user_defined_category=define_time_model_for_period(self.category or category, target_period=target_period),
            fuel=fuel,
            energy_usage_model={
                timestep: resolve_reference(
                    value=reference,
                    references=references.models,
                )
                for timestep, reference in define_time_model_for_period(
                    self.energy_usage_model, target_period=target_period
                ).items()
            },
        )

    def get_timestep_for_model(self, timestep: datetime, references: References) -> PumpModel:
        """
        TODO: Make general and make a general util method for yaml conversion
        Args:
            timestep:
            references:

        Returns:

        """
        if not isinstance(self.energy_usage_model, Dict):
            energy_model_reference = self.energy_usage_model
        else:
            energy_model_reference = define_time_model_for_period(
                self.energy_usage_model, target_period=Period(start=timestep, end=timestep)
            )  # TODO: Period is not the same as timestep...is this ok? we want the model at a given time ...

        energy_model = resolve_reference(
            value=energy_model_reference,
            references=references.models,
        )

        pump_model_for_timestep = create_pump_model(energy_model)

        return pump_model_for_timestep

    def stream_conditions_for_timestep(self, timestep: datetime, variables_map: VariablesMap) -> List[StreamConditions]:
        """
        Get stream conditions for a given timestep, inlet and outlet, index 0 and 1 respectively
        Args:
            timestep:
            variables_map:

        Returns:

        """

        stream_conditions = []
        for stream_type in ["inlet", "outlet"]:
            stream_condition = self.stream_conditions.get(stream_type)
            stream_conditions.append(
                StreamConditions(
                    id=generate_id(self.name, stream_type),
                    name=stream_type,
                    timestep=timestep,
                    rate=Rate(
                        value=list(
                            Expression.setup_from_expression(stream_condition.rate.value).evaluate(
                                variables=variables_map.variables, fill_length=1
                            )
                        )[0],
                        unit=stream_condition.rate.unit,
                    )
                    if stream_condition.rate is not None
                    else None,
                    pressure=Pressure(
                        value=list(
                            Expression.setup_from_expression(stream_condition.pressure.value).evaluate(
                                variables=variables_map.variables, fill_length=1
                            )
                        )[0],
                        unit=stream_condition.pressure.unit,
                    )
                    if stream_condition.pressure is not None
                    else None,
                    density=Density(
                        value=list(
                            Expression.setup_from_expression(stream_condition.fluid_density.value).evaluate(
                                variables=variables_map.variables, fill_length=1
                            )
                        )[0],
                        unit=stream_condition.fluid_density.unit,
                    )
                    if stream_condition.fluid_density is not None
                    else None,
                )
            )

            return stream_conditions

    def to_domain_model(
        self,
        references: References,  # need to resolve, but that should be handled "before"? or here? send in relevant reference?
        timestep: datetime,
    ) -> Pump:
        """
        Given a timestep, get the domain model for that timestep to calculate. In order to get domain models for all
        timesteps a yaml pump is valid at (given a yaml scenario), this function needs to be called for each date,
        and make sure that you have either a complete or corresponding reference list to that timestep.

        Information such as emission (fuel), regularity, consumption_type and categories are not handled in the core
        domain, and must be dealt with in other domains or in the use case/yaml layer etc.

        We may later introduce a temporal and spatial domain that handles that transparently.

        Args:
            references:
            timestep:

        Returns:

        """
        # TODO: Convert to stream day? OR done?

        return Pump(id=self.name, pump_model=self.get_timestep_for_model(timestep=timestep, references=references))

    # TODO is def from_domain(cls, pump: Pump) -> Self: relevant? Should it generate model as a string? or tuple? or with resolved and expanded reference?

    def to_domain_models(self, timesteps: List[datetime], references: References) -> TemporalModel[Pump]:
        """
        For every valid timestep, we extrapolate and create a full domain model representation of the pump

        TODO: Should "global time vector" and "global references" be "globally accessible", e.g. through a "service"?
        such as services provided in constructor to access these services to get it? both of these are yaml specific, as the
        other layers will give these directly, or not be relevant.

        Args:
            timesteps:
            references:

        Returns:

        """
        return TemporalModel(
            {timestep: self.to_domain_model(references=references, timestep=timestep) for timestep in timesteps}
        )
