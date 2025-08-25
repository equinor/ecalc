import datetime
from uuid import uuid4

import pytest

import libecalc.common.energy_usage_type
import libecalc.dto.fuel_type
from libecalc.common.component_type import ComponentType
from libecalc.common.temporal_model import TemporalModel
from libecalc.common.time_utils import Period
from libecalc.domain import regularity
from libecalc.domain.hydrocarbon_export import HydrocarbonExport
from libecalc.domain.infrastructure.energy_components.asset.asset import Asset
from libecalc.domain.infrastructure.energy_components.fuel_consumer.fuel_consumer import FuelConsumerComponent
from libecalc.domain.infrastructure.energy_components.installation.installation import InstallationComponent
from libecalc.domain.infrastructure.energy_components.legacy_consumer.system.consumer_function import (
    CompressorSystemConsumerFunction,
)
from libecalc.domain.infrastructure.energy_components.legacy_consumer.system.operational_setting import (
    ConsumerSystemOperationalSettingExpressions,
)
from libecalc.domain.infrastructure.energy_components.legacy_consumer.system.types import ConsumerSystemComponent
from libecalc.domain.infrastructure.path_id import PathID
from libecalc.domain.process.compressor import dto
from libecalc.domain.process.compressor.core import create_compressor_model
from libecalc.domain.regularity import Regularity
from libecalc.dto.emission import Emission
from libecalc.expression import Expression
from libecalc.presentation.flow_diagram.flow_diagram_dtos import Flow, FlowType, Node, NodeType
from tests.conftest import make_time_series_flow_rate

FUEL_NODE = Node(id="fuel-input", title="Fuel", type=NodeType.INPUT_OUTPUT_NODE)
INPUT_NODE = Node(id="input", title="Input", type=NodeType.INPUT_OUTPUT_NODE)
EMISSION_NODE = Node(id="emission-output", title="Emission", type=NodeType.INPUT_OUTPUT_NODE)

INSTALLATION_NAME = "Installation"

FUEL_FLOW = Flow(id="fuel-flow", label="Fuel", type=FlowType.FUEL)
EMISSIONS_FLOW = Flow(id="emission-flow", label="Emissions", type=FlowType.EMISSION)
ELECTRICITY_FLOW = Flow(
    id="electricity-flow",
    label="Electricity",
    type=FlowType.ELECTRICITY,
)


def compressor_system_compressor_fd(name: str) -> ConsumerSystemComponent:
    """Create a compressor system, only relevant property is the name when used to generate a FlowDiagram
    :param name:
    :return:
    """
    return ConsumerSystemComponent(
        name=name,
        facility_model=create_compressor_model(
            dto.CompressorSampled(
                energy_usage_values=[0, 4500, 9500],
                rate_values=[0, 5000, 10000],
                suction_pressure_values=[5, 5, 5],
                discharge_pressure_values=[50, 50, 50],
                energy_usage_type=libecalc.common.energy_usage_type.EnergyUsageType.FUEL,
                energy_usage_adjustment_constant=0,
                energy_usage_adjustment_factor=1.0,
            )
        ),
    )


@pytest.fixture
def fuel_type_fd() -> libecalc.dto.fuel_type.FuelType:
    return libecalc.dto.fuel_type.FuelType(
        id=uuid4(),
        name="fuel_gas",
        emissions=[
            Emission(
                name="co2",
                factor=Expression.setup_from_expression(value="2.20"),
            )
        ],
    )


@pytest.fixture
def compressor_system_consumer_dto_fd(
    fuel_type_fd, expression_evaluator_factory, make_time_series_flow_rate, make_time_series_pressure
) -> FuelConsumerComponent:
    expression_evaluator = expression_evaluator_factory.from_time_vector(
        [datetime.datetime(1900, 1, 1), datetime.datetime.max]
    )
    return FuelConsumerComponent(
        id=uuid4(),
        path_id=PathID("Compressor system 1"),
        component_type=ComponentType.COMPRESSOR_SYSTEM,
        fuel={Period(datetime.datetime(1900, 1, 1), datetime.datetime(2021, 1, 1)): fuel_type_fd},
        regularity=Regularity(
            expression_evaluator=expression_evaluator,
            target_period=expression_evaluator.get_period(),
            expression_input=1,
        ),
        energy_usage_model=TemporalModel(
            {
                Period(datetime.datetime(2018, 1, 1), datetime.datetime(2020, 1, 1)): CompressorSystemConsumerFunction(
                    consumer_components=[
                        compressor_system_compressor_fd("compressor1"),
                        compressor_system_compressor_fd("compressor2"),
                    ],
                    operational_settings_expressions=[
                        ConsumerSystemOperationalSettingExpressions(
                            rates=[
                                make_time_series_flow_rate(
                                    value=5, evaluator=expression_evaluator, regularity=regularity
                                ),
                                make_time_series_flow_rate(
                                    value=0, evaluator=expression_evaluator, regularity=regularity
                                ),
                            ],
                            suction_pressures=[make_time_series_pressure(value=3, evaluator=expression_evaluator)] * 2,
                            discharge_pressures=[make_time_series_pressure(value=200, evaluator=expression_evaluator)]
                            * 2,
                        ),
                        ConsumerSystemOperationalSettingExpressions(
                            rates=[
                                make_time_series_flow_rate(
                                    value=2.5, evaluator=expression_evaluator, regularity=regularity
                                )
                            ]
                            * 2,
                            suction_pressures=[make_time_series_pressure(value=3, evaluator=expression_evaluator)] * 2,
                            discharge_pressures=[make_time_series_pressure(value=200, evaluator=expression_evaluator)]
                            * 2,
                        ),
                    ],
                    power_loss_factor=None,
                ),
                Period(datetime.datetime(2020, 1, 1), datetime.datetime(2021, 1, 1)): CompressorSystemConsumerFunction(
                    consumer_components=[
                        compressor_system_compressor_fd("compressor1"),
                        compressor_system_compressor_fd("compressor2"),
                        compressor_system_compressor_fd("compressor3"),
                    ],
                    operational_settings_expressions=[
                        ConsumerSystemOperationalSettingExpressions(
                            rates=[
                                make_time_series_flow_rate(
                                    value=5, evaluator=expression_evaluator, regularity=regularity
                                ),
                                make_time_series_flow_rate(
                                    value=0, evaluator=expression_evaluator, regularity=regularity
                                ),
                                make_time_series_flow_rate(
                                    value=0, evaluator=expression_evaluator, regularity=regularity
                                ),
                            ],
                            suction_pressures=[make_time_series_pressure(value=3, evaluator=expression_evaluator)] * 3,
                            discharge_pressures=[make_time_series_pressure(value=200, evaluator=expression_evaluator)]
                            * 3,
                        ),
                        ConsumerSystemOperationalSettingExpressions(
                            rates=[
                                make_time_series_flow_rate(
                                    value=1.65, evaluator=expression_evaluator, regularity=regularity
                                ),
                                make_time_series_flow_rate(
                                    value=1.65, evaluator=expression_evaluator, regularity=regularity
                                ),
                                make_time_series_flow_rate(
                                    value=1.7, evaluator=expression_evaluator, regularity=regularity
                                ),
                            ],
                            suction_pressures=[make_time_series_pressure(value=3, evaluator=expression_evaluator)] * 3,
                            discharge_pressures=[make_time_series_pressure(value=200, evaluator=expression_evaluator)]
                            * 3,
                        ),
                    ],
                    power_loss_factor=None,
                ),
            }
        ),
        expression_evaluator=expression_evaluator,
    )


@pytest.fixture
def compressor_consumer_dto_fd(
    fuel_type_fd, expression_evaluator_factory, direct_expression_model_factory
) -> FuelConsumerComponent:
    expression_evaluator = expression_evaluator_factory.from_time_vector(
        [datetime.datetime(1900, 1, 1), datetime.datetime.max]
    )
    regularity = Regularity(
        expression_evaluator=expression_evaluator,
        target_period=expression_evaluator.get_period(),
        expression_input=1,
    )
    return FuelConsumerComponent(
        id=uuid4(),
        path_id=PathID("Compressor 1"),
        component_type=ComponentType.GENERIC,
        fuel={Period(datetime.datetime(1900, 1, 1), datetime.datetime(2021, 1, 1)): fuel_type_fd},
        energy_usage_model=TemporalModel(
            {
                Period(datetime.datetime(2019, 1, 1), datetime.datetime(2021, 1, 1)): direct_expression_model_factory(
                    expression=Expression.setup_from_expression(value=5),
                    energy_usage_type=libecalc.common.energy_usage_type.EnergyUsageType.FUEL,
                    expression_evaluator=expression_evaluator,
                    regularity=regularity,
                )
            }
        ),
        regularity=regularity,
        expression_evaluator=expression_evaluator,
    )


@pytest.fixture
def installation_with_dates_dto_fd(
    compressor_system_consumer_dto_fd: FuelConsumerComponent,
    compressor_consumer_dto_fd: FuelConsumerComponent,
    expression_evaluator_factory,
) -> Asset:
    expression_evaluator = expression_evaluator_factory.from_time_vector(
        time_vector=[datetime.datetime(1900, 1, 1), datetime.datetime(2021, 1, 1)]
    )
    regularity = Regularity(
        expression_evaluator=expression_evaluator,
        target_period=expression_evaluator.get_period(),
        expression_input=1,
    )
    return Asset(
        id=uuid4(),
        path_id=PathID("installation_with_dates"),
        installations=[
            InstallationComponent(
                id=uuid4(),
                path_id=PathID("Installation1"),
                fuel_consumers=[compressor_system_consumer_dto_fd, compressor_consumer_dto_fd],
                regularity=regularity,
                hydrocarbon_export=HydrocarbonExport(
                    expression_evaluator=expression_evaluator,
                    target_period=expression_evaluator.get_period(),
                    expression_input=0,
                    regularity=regularity,
                ),
                expression_evaluator=expression_evaluator,
            )
        ],
    )
