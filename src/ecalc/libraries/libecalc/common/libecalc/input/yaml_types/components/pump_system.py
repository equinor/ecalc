from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from libecalc import dto
from libecalc.common.time_utils import Period, define_time_model_for_period
from libecalc.dto.base import ComponentType
from libecalc.dto.types import ConsumptionType
from libecalc.expression import Expression
from libecalc.input.mappers.utils import resolve_and_validate_reference
from libecalc.input.yaml_entities import References
from libecalc.input.yaml_types.components.base import (
    ConsumerBase,
    ConsumerSystemOperationalConditionBase,
)
from libecalc.input.yaml_types.components.pump import Pump
from libecalc.input.yaml_types.temporal_model import TemporalModel
from pydantic import Field, confloat, root_validator, validator

opt_expr_list = Optional[List[str]]


class OperationalSettings(ConsumerSystemOperationalConditionBase):
    total_system_rate: Optional[str] = Field(
        None,
        title="Total system rate",
        description="The total system rate expression."
        "\n\nShould be used with RATE_FRACTIONS in OPERATIONAL_SETTINGS.",
    )
    rate_fractions: Optional[List[confloat(ge=0, le=1)]] = Field(
        None,
        title="Rate fractions",
        description="Rate fractions of total system rate, as a list of floats between 0 and 1."
        "\n\nThis requires TOTAL_SYSTEM_RATE to be defined."
        "\nThis is mutually exclusive with RATES.",
    )
    rates: opt_expr_list = Field(
        None,
        title="Rates",
        description="Rates [Sm3/day] as a list of expressions" "\n\nThis is mutually exclusive with RATE_FRACTIONS.",
    )
    inlet_pressure: Optional[str] = Field(
        None,
        title="Inlet pressure",
        description="Inlet pressure [bara] as a single expression"
        " This inlet pressure will be the same for all components in the consumer system.",
    )
    inlet_pressures: opt_expr_list = Field(
        None, title="Inlet pressures", description="Inlet pressures [bara] as a list of expressions."
    )
    outlet_pressure: Optional[str] = Field(
        None,
        title="Outlet pressure",
        description="Outlet pressure [bara] as a single expression"
        " This inlet pressure will be the same for all components in the consumer system.",
    )
    outlet_pressures: opt_expr_list = Field(
        None, title="Outlet pressures", description="Outlet pressures [bara] as a list of expressions."
    )
    fluid_density: Optional[str] = Field(
        None, title="FluidStream density", description="The fluid density [kg/m3] as a single expression."
    )
    fluid_densities: opt_expr_list = Field(
        None, title="FluidStream densities", description="The fluid density [kg/m3] as a list of expressions."
    )
    crossover: Optional[List[int]] = Field(
        None,
        title="Crossover",
        description="""
CROSSOVER specifies if rates are to be crossed over to another consumer if rate capacity is exceeded. If the energy \n
consumption calculation is not successful for a consumer, and the consumer has a valid cross-over defined, the \n
consumer will be allocated its maximum rate and the exceeding rate will be added to the cross-over consumer. \n
To avoid loops, a consumer can only be either receiving or giving away rate. For a cross-over to be valid, the \n
discharge pressure at the consumer "receiving" overshooting rate must be higher than or equal to the discharge \n
pressure of the "sending" consumer. This is because it is possible to choke pressure down to meet the outlet pressure \n
in a flow line with lower pressure, but not possible to "pressure up" in the crossover flow line. \n
Some examples show how the crossover logic works:\n\n
Crossover is given as and list of integer values for the first position is the first consumer, second position is \n
the second consumer, etc. The number specifies which consumer to send cross-over flow to, and 0 signifies no \n
cross-over possible. Note that we use 1-index here.\n\n
Example 1:\n
Two consumers where there is a cross-over such that if the rate for the first consumer exceeds its capacity, \n
the excess rate will be processed by the second consumer. The second consumer can not cross-over to anyone. \n\n
CROSSOVER: [2, 0]\n\n
Example 2:\n
The first and second consumers may both send exceeding rate to the third consumer if their capacity is exceeded.\n\n
CROSSOVER: [3,3,0]
""",
    )

    @validator("rate_fractions", always=True)
    def mutually_exclusive_rates(cls, v, values):
        if values.get("rates") is not None and v:
            raise ValueError("'RATE_FRACTIONS' and 'RATES' are mutually exclusive.")
        return v

    @validator("inlet_pressure", always=True)
    def mutually_exclusive_inlet_pressure(cls, v, values):
        if values.get("inlet_pressures") is not None and v:
            raise ValueError("'INLET_PRESSURE' and 'INLET_PRESSURES' are mutually exclusive.")
        return v

    @validator("outlet_pressure", always=True)
    def mutually_exclusive_outlet_pressure(cls, v, values):
        if values.get("outlet_pressures") is not None and v:
            raise ValueError("'OUTLET_PRESSURE' and 'OUTLET_PRESSURES' are mutually exclusive.")
        return v

    @validator("fluid_density", always=True)
    def mutually_exclusive_fluid_density(cls, v, values):
        if values.get("fluid_densities") is not None and v:
            raise ValueError("'FLUID_DENSITY' and 'FLUID_DENSITIES' are mutually exclusive.")
        return v


class PumpSystem(ConsumerBase):
    component_type: Literal[ComponentType.PUMP_SYSTEM_V2] = Field(
        ComponentType.PUMP_SYSTEM_V2,
        title="Type",
        description="The type of the component",
        alias="TYPE",
    )
    operational_settings: TemporalModel[List[OperationalSettings]]
    consumers: List[Pump]

    @root_validator
    def validate_operational_settings(cls, values):
        rate = values.get("rate")
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
            # Validate rates
            rate_fractions = operational_setting.rate_fractions
            rates = operational_setting.rates
            if rate_fractions is not None:
                if rate is None:
                    raise ValueError("RATE should be specified when using RATE_FRACTIONS.")
            elif rate_fractions is None and rates is None:
                raise ValueError("Either RATES or RATE_FRACTIONS should be specified.")

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
                if operational_setting.rates is not None:
                    rates = [Expression.setup_from_expression(rate) for rate in operational_setting.rates]
                else:
                    rates = [
                        Expression.multiply(
                            Expression.setup_from_expression(self.rate), Expression.setup_from_expression(rate_fraction)
                        )
                        for rate_fraction in operational_setting.rate_fractions
                    ]
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
        )
