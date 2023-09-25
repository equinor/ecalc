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
from libecalc.input.yaml_types.components.yaml_compressor import YamlCompressor
from libecalc.input.yaml_types.yaml_temporal_model import YamlTemporalModel
from pydantic import Field, root_validator, validator

opt_expr_list = Optional[List[ExpressionType]]


class YamlCompressorSystemOperationalSettings(YamlConsumerSystemOperationalConditionBase):
    class Config:
        title = "CompressorSystemOperationalSettings"

    rates: List[ExpressionType] = Field(
        None,
        title="Rates",
        description="Rates [Sm3/day] as a list of expressions" "\n\nThis is mutually exclusive with RATE_FRACTIONS.",
    )
    inlet_pressure: Optional[ExpressionType] = Field(
        None,
        title="Inlet pressure",
        description="Inlet pressure [bara] as a single expression"
        " This inlet pressure will be the same for all components in the consumer system.",
    )
    inlet_pressures: opt_expr_list = Field(
        None, title="Inlet pressures", description="Inlet pressures [bara] as a list of expressions."
    )
    outlet_pressure: Optional[ExpressionType] = Field(
        None,
        title="Outlet pressure",
        description="Outlet pressure [bara] as a single expression"
        " This inlet pressure will be the same for all components in the consumer system.",
    )
    outlet_pressures: opt_expr_list = Field(
        None, title="Outlet pressures", description="Outlet pressures [bara] as a list of expressions."
    )
    crossover: Optional[List[int]] = Field(
        None,
        title="Crossover",
        description=(
            "CROSSOVER specifies if rates are to be crossed over to another consumer if rate capacity is exceeded. If the energy"
            " consumption calculation is not successful for a consumer, and the consumer has a valid cross-over defined, the"
            " consumer will be allocated its maximum rate and the exceeding rate will be added to the cross-over consumer.\n"
            "To avoid loops, a consumer can only be either receiving or giving away rate. For a cross-over to be valid, the"
            ' discharge pressure at the consumer "receiving" overshooting rate must be higher than or equal to the discharge'
            ' pressure of the "sending" consumer. This is because it is possible to choke pressure down to meet the outlet pressure'
            ' in a flow line with lower pressure, but not possible to "pressure up" in the crossover flow line.\n'
            "Some examples show how the crossover logic works:\n"
            "Crossover is given as and list of integer values for the first position is the first consumer, second position is"
            " the second consumer, etc. The number specifies which consumer to send cross-over flow to, and 0 signifies no"
            " cross-over possible. Note that we use 1-index here.\n"
            "Example 1:\n"
            "Two consumers where there is a cross-over such that if the rate for the first consumer exceeds its capacity,"
            " the excess rate will be processed by the second consumer. The second consumer can not cross-over to anyone.\n"
            "CROSSOVER: [2, 0]\n"
            "Example 2:\n"
            "The first and second consumers may both send exceeding rate to the third consumer if their capacity is exceeded.\n"
            "CROSSOVER: [3,3,0]"
        ),
    )

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


class YamlCompressorSystem(YamlConsumerBase):
    class Config:
        title = "CompressorSystem"

    component_type: Literal[ComponentType.COMPRESSOR_SYSTEM_V2] = Field(
        ComponentType.COMPRESSOR_SYSTEM_V2,
        title="Type",
        description="The type of the component",
        alias="TYPE",
    )

    operational_settings: YamlTemporalModel[List[YamlCompressorSystemOperationalSettings]]
    consumers: List[YamlCompressor]

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

        parsed_operational_settings: Dict[datetime, Any] = {}
        temporal_operational_settings = define_time_model_for_period(
            self.operational_settings, target_period=target_period
        )
        for timestep, operational_settings in temporal_operational_settings.items():
            parsed_operational_settings[timestep] = []
            for operational_setting in operational_settings:
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

                parsed_operational_settings[timestep].append(
                    dto.components.CompressorSystemOperationalSetting(
                        rates=rates,
                        inlet_pressures=[Expression.setup_from_expression(pressure) for pressure in inlet_pressures],
                        outlet_pressures=[Expression.setup_from_expression(pressure) for pressure in outlet_pressures],
                        crossover=operational_setting.crossover or [0] * number_of_compressors,
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

        return dto.components.CompressorSystem(
            name=self.name,
            user_defined_category=define_time_model_for_period(self.category, target_period=target_period),
            regularity=regularity,
            consumes=consumes,
            operational_settings=parsed_operational_settings,
            compressors=compressors,
            fuel=fuel,
        )
