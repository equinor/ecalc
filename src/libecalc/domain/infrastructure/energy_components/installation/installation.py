from typing import Annotated, Literal, Optional, Union

from pydantic import Field, field_validator, model_validator
from pydantic_core.core_schema import ValidationInfo

from libecalc.application.energy.energy_component import EnergyComponent
from libecalc.common.component_type import ComponentType
from libecalc.common.string.string_utils import generate_id
from libecalc.common.time_utils import Period
from libecalc.domain.infrastructure.energy_components.base.component_dto import BaseComponent
from libecalc.domain.infrastructure.energy_components.consumer_system.consumer_system_dto import ConsumerSystem
from libecalc.domain.infrastructure.energy_components.fuel_consumer.fuel_consumer import FuelConsumer
from libecalc.domain.infrastructure.energy_components.generator_set.generator_set_dto import GeneratorSet
from libecalc.dto.component_graph import ComponentGraph
from libecalc.dto.types import InstallationUserDefinedCategoryType
from libecalc.dto.utils.validators import (
    convert_expression,
    validate_temporal_model,
)
from libecalc.expression import Expression
from libecalc.presentation.yaml.yaml_keywords import EcalcYamlKeywords
from libecalc.presentation.yaml.yaml_types.emitters.yaml_venting_emitter import (
    YamlVentingEmitter,
)


class Installation(BaseComponent, EnergyComponent):
    component_type: Literal[ComponentType.INSTALLATION] = ComponentType.INSTALLATION

    user_defined_category: Optional[InstallationUserDefinedCategoryType] = Field(default=None, validate_default=True)
    hydrocarbon_export: dict[Period, Expression]
    fuel_consumers: list[
        Annotated[
            Union[GeneratorSet, FuelConsumer, ConsumerSystem],
            Field(discriminator="component_type"),
        ]
    ] = Field(default_factory=list)
    venting_emitters: list[YamlVentingEmitter] = Field(default_factory=list)

    def is_fuel_consumer(self) -> bool:
        return True

    def is_electricity_consumer(self) -> bool:
        # Should maybe be True if power from shore?
        return False

    def is_provider(self) -> bool:
        return False

    def is_container(self) -> bool:
        return True

    def get_component_process_type(self) -> ComponentType:
        return self.component_type

    def get_name(self) -> str:
        return self.name

    @property
    def id(self) -> str:
        return generate_id(self.name)

    _validate_installation_temporal_model = field_validator("hydrocarbon_export")(validate_temporal_model)

    _convert_expression_installation = field_validator("regularity", "hydrocarbon_export", mode="before")(
        convert_expression
    )

    @field_validator("user_defined_category", mode="before")
    def check_user_defined_category(cls, user_defined_category, info: ValidationInfo):
        # Provide which value and context to make it easier for user to correct wrt mandatory changes.
        if user_defined_category is not None:
            if user_defined_category not in list(InstallationUserDefinedCategoryType):
                name_context_str = ""
                if (name := info.data.get("name")) is not None:
                    name_context_str = f"with the name {name}"

                raise ValueError(
                    f"CATEGORY: {user_defined_category} is not allowed for {cls.__name__} {name_context_str}. Valid categories are: {[str(installation_user_defined_category.value) for installation_user_defined_category in InstallationUserDefinedCategoryType]}"
                )

        return user_defined_category

    @model_validator(mode="after")
    def check_fuel_consumers_or_venting_emitters_exist(self):
        try:
            if self.fuel_consumers or self.venting_emitters:
                return self
        except AttributeError:
            raise ValueError(
                f"Keywords are missing:\n It is required to specify at least one of the keywords "
                f"{EcalcYamlKeywords.fuel_consumers}, {EcalcYamlKeywords.generator_sets} or {EcalcYamlKeywords.installation_venting_emitters} in the model.",
            ) from None

    def get_graph(self) -> ComponentGraph:
        graph = ComponentGraph()
        graph.add_node(self)
        for component in [*self.fuel_consumers, *self.venting_emitters]:
            if hasattr(component, "get_graph"):
                graph.add_subgraph(component.get_graph())
            else:
                graph.add_node(component)

            graph.add_edge(self.id, component.id)

        return graph
