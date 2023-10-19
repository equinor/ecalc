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
from libecalc.input.yaml_types.components.yaml_pump import YamlPump
from pydantic import Field, root_validator, validator

opt_expr_list = Optional[List[ExpressionType]]


class YamlPumpSystemOperationalSettings(YamlConsumerSystemOperationalConditionBase):
    class Config:
        title = "PumpSystemOperationalSettings"

    fluid_density: Optional[ExpressionType] = Field(
        None, title="FluidStream density", description="The fluid density [kg/m3] as a single expression."
    )
    fluid_densities: opt_expr_list = Field(
        None, title="FluidStream densities", description="The fluid density [kg/m3] as a list of expressions."
    )

    @validator("fluid_density", always=True)
    def mutually_exclusive_fluid_density(cls, v, values):
        if values.get("fluid_densities") is not None and v:
            raise ValueError("'FLUID_DENSITY' and 'FLUID_DENSITIES' are mutually exclusive.")
        return v


class YamlPumpSystem(YamlConsumerBase):
    class Config:
        title = "PumpSystem"

    component_type: Literal[ComponentType.PUMP_SYSTEM_V2] = Field(
        ComponentType.PUMP_SYSTEM_V2,
        title="Type",
        description="The type of the component",
        alias="TYPE",
    )

    component_conditions: YamlSystemComponentConditions = Field(
        None,
        title="System component conditions",
        description="Contains conditions for the component, in this case the system.",
    )

    operational_settings: List[YamlPumpSystemOperationalSettings]

    consumers: List[YamlPump]

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

            fluid_densities = operational_setting.fluid_densities
            fluid_density = operational_setting.fluid_density
            if fluid_densities is None and fluid_density is None:
                raise ValueError("Either FLUID_DENSITY or FLUID_DENSITIES should be specified.")
            elif fluid_densities is not None and fluid_density is not None:
                raise ValueError("Either FLUID_DENSITY or FLUID_DENSITIES should be specified, not both.")

        return values

    def to_dto(
        self,
        regularity: Dict[datetime, Expression],
        consumes: ConsumptionType,
        references: References,
        target_period: Period,
        fuel: Optional[Dict[datetime, dto.types.FuelType]] = None,
    ) -> dto.components.PumpSystem:
        number_of_pumps = len(self.consumers)

        parsed_operational_settings: List[dto.components.PumpSystemOperationalSetting] = []
        for operational_setting in self.operational_settings:
            inlet_pressures = (
                operational_setting.inlet_pressures
                if operational_setting.inlet_pressures is not None
                else [operational_setting.inlet_pressure] * number_of_pumps
            )
            outlet_pressures = (
                operational_setting.outlet_pressures
                if operational_setting.outlet_pressures is not None
                else [operational_setting.outlet_pressure] * number_of_pumps
            )
            rates = [Expression.setup_from_expression(rate) for rate in operational_setting.rates]

            fluid_densities = (
                operational_setting.fluid_densities
                if operational_setting.fluid_densities is not None
                else [operational_setting.fluid_density] * number_of_pumps
            )
            parsed_operational_settings.append(
                dto.components.PumpSystemOperationalSetting(
                    rates=rates,
                    inlet_pressures=[Expression.setup_from_expression(pressure) for pressure in inlet_pressures],
                    outlet_pressures=[Expression.setup_from_expression(pressure) for pressure in outlet_pressures],
                    fluid_density=[
                        Expression.setup_from_expression(fluid_density) for fluid_density in fluid_densities
                    ],
                )
            )

        pumps: List[dto.components.PumpComponent] = [
            dto.components.PumpComponent(
                consumes=consumes,
                regularity=regularity,
                name=pump.name,
                user_defined_category=define_time_model_for_period(
                    pump.category or self.category, target_period=target_period
                ),
                fuel=fuel,
                energy_usage_model={
                    timestep: resolve_and_validate_reference(
                        value=reference,
                        references=references.models,
                    )
                    for timestep, reference in define_time_model_for_period(
                        pump.energy_usage_model, target_period=target_period
                    ).items()
                },
            )
            for pump in self.consumers
        ]

        pump_name_to_id_map = {pump.name: pump.id for pump in pumps}

        if self.component_conditions is not None:
            component_conditions = SystemComponentConditions(
                crossover=[
                    Crossover(
                        from_component_id=pump_name_to_id_map[crossover_stream.from_],
                        to_component_id=pump_name_to_id_map[crossover_stream.to],
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

        return dto.components.PumpSystem(
            name=self.name,
            user_defined_category=define_time_model_for_period(self.category, target_period=target_period),
            regularity=regularity,
            consumes=consumes,
            component_conditions=component_conditions,
            operational_settings=parsed_operational_settings,
            pumps=pumps,
            fuel=fuel,
        )
