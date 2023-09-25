from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from libecalc import dto
from libecalc.common.time_utils import Period, define_time_model_for_period
from libecalc.dto.base import ComponentType
from libecalc.dto.types import ConsumptionType
from libecalc.expression import Expression
from libecalc.expression.expression import ExpressionType
from libecalc.input.mappers.utils import resolve_and_validate_reference
from libecalc.input.yaml_entities import References
from libecalc.input.yaml_types.components.yaml_base import (
    YamlConsumerBase,
    YamlConsumerSystemOperationalConditionBase,
)
from libecalc.input.yaml_types.components.yaml_pump import YamlPump
from libecalc.input.yaml_types.yaml_temporal_model import YamlTemporalModel
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
    operational_settings: YamlTemporalModel[List[YamlPumpSystemOperationalSettings]]
    consumers: List[YamlPump]

    @root_validator
    def validate_operational_settings(cls, values):
        operational_settings = values.get("operational_settings")

        if operational_settings is None:
            return values

        if isinstance(operational_settings, dict):
            flattened_operational_settings = []
            for operational_setting in operational_settings.values():
                flattened_operational_settings.extend(operational_setting)
        else:
            flattened_operational_settings = operational_settings

        for operational_setting in flattened_operational_settings:
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

        parsed_operational_settings: Dict[datetime, Any] = {}
        temporal_operational_settings = define_time_model_for_period(
            time_model_data=self.operational_settings, target_period=target_period
        )

        for timestep, operational_settings in temporal_operational_settings.items():
            parsed_operational_settings[timestep] = []
            for operational_setting in operational_settings:
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
                parsed_operational_settings[timestep].append(
                    dto.components.PumpSystemOperationalSetting(
                        rates=rates,
                        inlet_pressures=[Expression.setup_from_expression(pressure) for pressure in inlet_pressures],
                        outlet_pressures=[Expression.setup_from_expression(pressure) for pressure in outlet_pressures],
                        crossover=operational_setting.crossover or [0] * number_of_pumps,
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

        return dto.components.PumpSystem(
            name=self.name,
            user_defined_category=define_time_model_for_period(self.category, target_period=target_period),
            regularity=regularity,
            consumes=consumes,
            operational_settings=parsed_operational_settings,
            pumps=pumps,
            fuel=fuel,
        )
