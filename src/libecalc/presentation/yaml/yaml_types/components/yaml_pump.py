from datetime import datetime
from typing import Dict, List, Literal, Optional

from pydantic import Field

from libecalc import dto
from libecalc.common.string.string_utils import generate_id
from libecalc.common.temporal_equipment import TemporalEquipment
from libecalc.common.temporal_model import TemporalModel
from libecalc.common.time_utils import (
    Period,
    define_time_model_for_period,
)
from libecalc.core.consumers.pump import Pump
from libecalc.core.models.pump import create_pump_model
from libecalc.domain.stream_conditions import Density, Pressure, Rate, StreamConditions
from libecalc.dto import PumpModel, VariablesMap
from libecalc.dto.base import ComponentType, ConsumerUserDefinedCategoryType
from libecalc.dto.components import PumpComponent
from libecalc.dto.types import ConsumptionType
from libecalc.expression import Expression
from libecalc.presentation.yaml.mappers.utils import resolve_reference
from libecalc.presentation.yaml.yaml_entities import References
from libecalc.presentation.yaml.yaml_types.components.system.yaml_consumer import (
    YamlConsumerStreamConditions,
)
from libecalc.presentation.yaml.yaml_types.components.yaml_base import (
    YamlConsumerBase,
)
from libecalc.presentation.yaml.yaml_types.yaml_temporal_model import YamlTemporalModel


class YamlPump(YamlConsumerBase):
    """
    V2 only.

    This DTO represents the pump in the yaml, and must therefore be a 1:1 to the yaml for a pump.

    It currently contains a simple string and dict mapping to the values in the YAML, and must therefore be parsed and resolved before being used.
    We may want to add the parsing and resolving here, to avoid an additional layer for parsing and resolving ...
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

    # TODO: Currently we share the stream conditions between consumer system and pump. Might change if they deviate ...
    # TODO: We may also want to enforce the names of the streams, and e.g. limit to 1 in -and output stream ...? At least we need to know what is in and out ...
    stream_conditions: Optional[YamlConsumerStreamConditions]

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
        Deprecated. Please use to_domain instead.

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

    def get_model_for_timestep(self, timestep: datetime, references: References) -> PumpModel:
        """
        For any timestep in the global time vector, we can get a time agnostic domain model for that point in time.

        Currently it returns a DTO representation of the Pump, containing all parameters required to calculate a pump ...

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
            )

        # TODO: Assume one, ok?
        key = next(iter(energy_model_reference))
        val = energy_model_reference[key]

        energy_model = resolve_reference(
            value=val,
            references=references.models,
        )

        pump_model_for_timestep = create_pump_model(energy_model)

        return pump_model_for_timestep

    def all_stream_conditions(self, variables_map: VariablesMap) -> Dict[datetime, List[StreamConditions]]:
        """
        For every timestep in the global time vector, we can create a map of all stream conditions required to calculate a pump

        Args:
            variables_map:

        Returns:

        """
        stream_conditions: Dict[datetime, List[StreamConditions]] = {}
        timevector = variables_map.time_vector
        for timestep in timevector:
            stream_conditions[timestep] = self.stream_conditions_for_timestep(timestep, variables_map)

        return stream_conditions

    def stream_conditions_for_timestep(self, timestep: datetime, variables_map: VariablesMap) -> List[StreamConditions]:
        """
        Get stream conditions for a given timestep, inlet and outlet, index 0 and 1 respectively

        TODO: Enforce names and limit to 1 in and output stream?

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
        references: References,
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

        return Pump(
            id=generate_id(self.name), pump_model=self.get_model_for_timestep(timestep=timestep, references=references)
        )

    def to_temporal_domain_models(
        self,
        timesteps: List[datetime],
        references: References,
        fuel: Optional[Dict[datetime, dto.types.FuelType]],
    ) -> TemporalEquipment[Pump]:
        """
        The temporal domain model is the thin later on top of the domain models, representing all the domain models for
        the entire global time vector

        For every valid timestep, we extrapolate and create a full domain model representation of the pump

        Args:
            timesteps:
            references:
            fuel:

        Returns:

        """
        return TemporalEquipment(
            id=generate_id(self.name),
            name=self.name,
            component_type=ComponentType.PUMP_V2,
            user_defined_category={timestep: ConsumerUserDefinedCategoryType(self.category) for timestep in timesteps},
            fuel=fuel,
            data=TemporalModel(
                {timestep: self.to_domain_model(references=references, timestep=timestep) for timestep in timesteps}
            ),
        )
