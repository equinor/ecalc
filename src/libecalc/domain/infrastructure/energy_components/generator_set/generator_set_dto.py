from typing import Annotated, Literal, Optional, Union

from pydantic import Field, field_validator, model_validator
from pydantic_core.core_schema import ValidationInfo

from libecalc.application.energy.component_energy_context import ComponentEnergyContext
from libecalc.application.energy.emitter import Emitter
from libecalc.application.energy.energy_component import EnergyComponent
from libecalc.application.energy.energy_model import EnergyModel
from libecalc.common.component_type import ComponentType
from libecalc.common.temporal_model import TemporalModel
from libecalc.common.time_utils import Period
from libecalc.common.variables import ExpressionEvaluator
from libecalc.core.models.generator import GeneratorModelSampled
from libecalc.core.result import EcalcModelResult
from libecalc.core.result.emission import EmissionResult
from libecalc.domain.infrastructure.energy_components.base.component_dto import BaseEquipment
from libecalc.domain.infrastructure.energy_components.consumer_system.consumer_system_dto import ConsumerSystem
from libecalc.domain.infrastructure.energy_components.electricity_consumer.electricity_consumer import (
    ElectricityConsumer,
)
from libecalc.domain.infrastructure.energy_components.fuel_model.fuel_model import FuelModel
from libecalc.domain.infrastructure.energy_components.generator_set.generator_set import Genset
from libecalc.domain.infrastructure.energy_components.utils import _convert_keys_in_dictionary_from_str_to_periods
from libecalc.dto.component_graph import ComponentGraph
from libecalc.dto.fuel_type import FuelType
from libecalc.dto.models import GeneratorSetSampled
from libecalc.dto.utils.validators import (
    ExpressionType,
    validate_temporal_model,
)
from libecalc.presentation.yaml.ltp_validation import (
    validate_generator_set_power_from_shore,
)


class GeneratorSet(BaseEquipment, Emitter, EnergyComponent):
    component_type: Literal[ComponentType.GENERATOR_SET] = ComponentType.GENERATOR_SET
    fuel: dict[Period, FuelType]
    generator_set_model: dict[Period, GeneratorSetSampled]
    consumers: list[
        Annotated[
            Union[ElectricityConsumer, ConsumerSystem],
            Field(discriminator="component_type"),
        ]
    ] = Field(default_factory=list)
    cable_loss: Optional[ExpressionType] = Field(
        None,
        title="CABLE_LOSS",
        description="Power loss in cables from shore. " "Used to calculate onshore delivery/power supply onshore.",
    )
    max_usage_from_shore: Optional[ExpressionType] = Field(
        None, title="MAX_USAGE_FROM_SHORE", description="The peak load/effect that is expected for one hour, per year."
    )

    def is_fuel_consumer(self) -> bool:
        return True

    def is_electricity_consumer(self) -> bool:
        return False

    def is_provider(self) -> bool:
        return True

    def is_container(self) -> bool:
        return False

    def get_component_process_type(self) -> ComponentType:
        return self.component_type

    def get_name(self) -> str:
        return self.name

    def evaluate_energy_usage(
        self, expression_evaluator: ExpressionEvaluator, context: ComponentEnergyContext
    ) -> dict[str, EcalcModelResult]:
        consumer_results: dict[str, EcalcModelResult] = {}
        fuel_consumer = Genset(
            id=self.id,
            name=self.name,
            temporal_generator_set_model=TemporalModel(
                {
                    period: GeneratorModelSampled(
                        fuel_values=model.fuel_values,
                        power_values=model.power_values,
                        energy_usage_adjustment_constant=model.energy_usage_adjustment_constant,
                        energy_usage_adjustment_factor=model.energy_usage_adjustment_factor,
                    )
                    for period, model in self.generator_set_model.items()
                }
            ),
        )

        consumer_results[self.id] = EcalcModelResult(
            component_result=fuel_consumer.evaluate(
                expression_evaluator=expression_evaluator,
                power_requirement=context.get_power_requirement(),
            ),
            models=[],
            sub_components=[],
        )

        return consumer_results

    def evaluate_emissions(
        self,
        energy_context: ComponentEnergyContext,
        energy_model: EnergyModel,
        expression_evaluator: ExpressionEvaluator,
    ) -> Optional[dict[str, EmissionResult]]:
        fuel_model = FuelModel(self.fuel)
        fuel_usage = energy_context.get_fuel_usage()

        assert fuel_usage is not None

        return fuel_model.evaluate_emissions(
            expression_evaluator=expression_evaluator,
            fuel_rate=fuel_usage.values,
        )

    _validate_genset_temporal_models = field_validator("generator_set_model", "fuel")(validate_temporal_model)

    @field_validator("user_defined_category", mode="before")
    @classmethod
    def check_mandatory_category_for_generator_set(cls, user_defined_category, info: ValidationInfo):
        """This could be handled automatically with Pydantic, but I want to inform the users in a better way, in
        particular since we introduced a breaking change for this to be mandatory for GeneratorSets in v7.2.
        """
        if user_defined_category is None or user_defined_category == "":
            raise ValueError(f"CATEGORY is mandatory and must be set for '{info.data.get('name', cls.__name__)}'")

        return user_defined_category

    @field_validator("generator_set_model", mode="before")
    @classmethod
    def check_generator_set_model(cls, generator_set_model, info: ValidationInfo):
        if isinstance(generator_set_model, dict) and len(generator_set_model.values()) > 0:
            generator_set_model = _convert_keys_in_dictionary_from_str_to_periods(generator_set_model)
        return generator_set_model

    @field_validator("fuel", mode="before")
    @classmethod
    def check_fuel(cls, fuel, info: ValidationInfo):
        """
        Make sure that temporal models are converted to Period objects if they are strings
        """
        if isinstance(fuel, dict) and len(fuel.values()) > 0:
            fuel = _convert_keys_in_dictionary_from_str_to_periods(fuel)
        return fuel

    @model_validator(mode="after")
    def check_power_from_shore(self):
        _check_power_from_shore_attributes = validate_generator_set_power_from_shore(
            cable_loss=self.cable_loss,
            max_usage_from_shore=self.max_usage_from_shore,
            model_fields=self.model_fields,
            category=self.user_defined_category,
        )

        return self

    def get_graph(self) -> ComponentGraph:
        graph = ComponentGraph()
        graph.add_node(self)
        for electricity_consumer in self.consumers:
            if hasattr(electricity_consumer, "get_graph"):
                graph.add_subgraph(electricity_consumer.get_graph())
            else:
                graph.add_node(electricity_consumer)

            graph.add_edge(self.id, electricity_consumer.id)

        return graph
