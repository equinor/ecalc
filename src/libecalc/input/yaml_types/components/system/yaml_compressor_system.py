from datetime import datetime
from typing import Dict, List, Literal, Optional

from libecalc import dto
from libecalc.common.time_utils import Period, define_time_model_for_period
from libecalc.dto.base import ComponentType
from libecalc.dto.components import Crossover, SystemComponentConditions
from libecalc.dto.types import ConsumptionType
from libecalc.expression import Expression
from libecalc.expression.expression import ExpressionType
from libecalc.input.mappers.utils import resolve_and_validate_reference
from libecalc.input.yaml_entities import References
from libecalc.input.yaml_types.components.system.yaml_system_component_conditions import (
    YamlSystemComponentConditions,
)
from libecalc.input.yaml_types.components.yaml_base import (
    YamlConsumerBase,
    YamlConsumerSystemOperationalConditionBase,
)
from libecalc.input.yaml_types.components.yaml_compressor import YamlCompressor
from pydantic import Field, root_validator

opt_expr_list = Optional[List[ExpressionType]]


class YamlCompressorSystemOperationalSettings(YamlConsumerSystemOperationalConditionBase):
    class Config:
        title = "CompressorSystemOperationalSettings"


class YamlCompressorSystem(YamlConsumerBase):
    class Config:
        title = "CompressorSystem"

    component_type: Literal[ComponentType.COMPRESSOR_SYSTEM_V2] = Field(
        ComponentType.COMPRESSOR_SYSTEM_V2,
        title="Type",
        description="The type of the component",
        alias="TYPE",
    )

    component_conditions: YamlSystemComponentConditions = Field(
        None,
        title="System component conditions",
        description="Contains conditions for the component, in this case the system.",
    )

    operational_settings: List[YamlCompressorSystemOperationalSettings]
    consumers: List[YamlCompressor]

    @root_validator
    def validate_operational_settings(cls, values):
        operational_settings = values.get("operational_settings")

        if operational_settings is None:
            return values

        for operational_setting in operational_settings:
            # Validate pressures
            inlet_pressures = operational_setting.inlet_pressures
            inlet_pressure = operational_setting.inlet_pressure
            if inlet_pressures is None and inlet_pressure is None:
                raise ValueError("Either INLET_PRESSURE or INLET_PRESSURES should be specified.")
            elif inlet_pressures is not None and inlet_pressure is not None:
                raise ValueError("Either INLET_PRESSURE or INLET_PRESSURES should be specified, not both.")

            outlet_pressures = operational_setting.outlet_pressures
            outlet_pressure = operational_setting.outlet_pressure
            if outlet_pressures is None and outlet_pressure is None:
                raise ValueError("Either OUTLET_PRESSURE or OUTLET_PRESSURES should be specified.")
            elif outlet_pressures is not None and outlet_pressure is not None:
                raise ValueError("Either OUTLET_PRESSURE or OUTLET_PRESSURES should be specified, not both.")

        return values

    def to_dto(
        self,
        regularity: Dict[datetime, Expression],
        consumes: ConsumptionType,
        references: References,
        target_period: Period,
        fuel: Optional[Dict[datetime, dto.types.FuelType]] = None,
    ) -> dto.components.CompressorSystem:
        number_of_compressors = len(self.consumers)

        parsed_operational_settings: List[dto.components.CompressorSystemOperationalSetting] = []
        for operational_setting in self.operational_settings:
            inlet_pressures = (
                operational_setting.inlet_pressures
                if operational_setting.inlet_pressures is not None
                else [operational_setting.inlet_pressure] * number_of_compressors
            )
            outlet_pressures = (
                operational_setting.outlet_pressures
                if operational_setting.outlet_pressures is not None
                else [operational_setting.outlet_pressure] * number_of_compressors
            )
            rates = [Expression.setup_from_expression(rate) for rate in operational_setting.rates]

            parsed_operational_settings.append(
                dto.components.CompressorSystemOperationalSetting(
                    rates=rates,
                    inlet_pressures=[Expression.setup_from_expression(pressure) for pressure in inlet_pressures],
                    outlet_pressures=[Expression.setup_from_expression(pressure) for pressure in outlet_pressures],
                )
            )

        compressors: List[dto.components.CompressorComponent] = [
            dto.components.CompressorComponent(
                consumes=consumes,
                regularity=regularity,
                name=compressor.name,
                user_defined_category=define_time_model_for_period(
                    compressor.category or self.category, target_period=target_period
                ),
                fuel=fuel,
                energy_usage_model={
                    timestep: resolve_and_validate_reference(
                        value=reference,
                        references=references.models,
                    )
                    for timestep, reference in define_time_model_for_period(
                        compressor.energy_usage_model, target_period=target_period
                    ).items()
                },
            )
            for compressor in self.consumers
        ]

        compressor_name_to_id_map = {compressor.name: compressor.id for compressor in compressors}

        if self.component_conditions is not None:
            component_conditions = SystemComponentConditions(
                crossover=[
                    Crossover(
                        from_component_id=compressor_name_to_id_map[crossover_stream.from_],
                        to_component_id=compressor_name_to_id_map[crossover_stream.to],
                        stream_name=crossover_stream.name,
                    )
                    for crossover_stream in self.component_conditions.crossover
                ]
                if self.component_conditions.crossover is not None
                else [],
            )
        else:
            component_conditions = SystemComponentConditions(
                crossover=[],
            )

        return dto.components.CompressorSystem(
            name=self.name,
            user_defined_category=define_time_model_for_period(self.category, target_period=target_period),
            regularity=regularity,
            consumes=consumes,
            component_conditions=component_conditions,
            operational_settings=parsed_operational_settings,
            compressors=compressors,
            fuel=fuel,
        )
