import datetime
from uuid import uuid4

import pytest

import libecalc.common.energy_usage_type
import libecalc.dto.fuel_type
from libecalc.common.component_type import ComponentType
from libecalc.common.temporal_model import TemporalModel
from libecalc.common.time_utils import Period
from libecalc.domain.energy import EnergyComponent, EnergyModel
from libecalc.domain.hydrocarbon_export import HydrocarbonExport
from libecalc.domain.infrastructure.energy_components.fuel_consumer.fuel_consumer import FuelConsumerComponent
from libecalc.domain.infrastructure.energy_components.installation.installation import InstallationComponent
from libecalc.domain.infrastructure.energy_components.legacy_consumer.system.consumer_function import (
    ConsumerSystemConsumerFunction,
)
from libecalc.domain.infrastructure.energy_components.legacy_consumer.system.operational_setting import (
    ConsumerSystemOperationalSettingExpressions,
)
from libecalc.domain.infrastructure.energy_components.legacy_consumer.system.types import ConsumerSystemComponent
from libecalc.domain.process.compressor.core.sampled import CompressorModelSampled
from libecalc.domain.regularity import Regularity
from libecalc.dto.emission import Emission
from libecalc.expression import Expression
from libecalc.presentation.flow_diagram.flow_diagram_dtos import Flow, FlowType, Node, NodeType
from libecalc.domain.energy.energy_component import EnergyContainerID

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
        facility_model=CompressorModelSampled(
            energy_usage_values=[0, 4500, 9500],
            rate_values=[0, 5000, 10000],
            suction_pressure_values=[5, 5, 5],
            discharge_pressure_values=[50, 50, 50],
            energy_usage_type=libecalc.common.energy_usage_type.EnergyUsageType.FUEL,
            energy_usage_adjustment_constant=0,
            energy_usage_adjustment_factor=1.0,
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
    regularity = Regularity(
        expression_evaluator=expression_evaluator,
        target_period=expression_evaluator.get_period(),
        expression_input=1,
    )
    return FuelConsumerComponent(
        id=uuid4(),
        name="Compressor system 1",
        component_type=ComponentType.COMPRESSOR_SYSTEM,
        fuel=TemporalModel({Period(datetime.datetime(1900, 1, 1), datetime.datetime(2021, 1, 1)): fuel_type_fd}),
        regularity=regularity,
        energy_usage_model=TemporalModel(
            {
                Period(datetime.datetime(2018, 1, 1), datetime.datetime(2020, 1, 1)): ConsumerSystemConsumerFunction(
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
                Period(datetime.datetime(2020, 1, 1), datetime.datetime(2021, 1, 1)): ConsumerSystemConsumerFunction(
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
        name="Compressor 1",
        component_type=ComponentType.GENERIC,
        fuel=TemporalModel({Period(datetime.datetime(1900, 1, 1), datetime.datetime(2021, 1, 1)): fuel_type_fd}),
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


class InstallationEnergyContainer(EnergyComponent):
    def __init__(self, id: EnergyContainerID, name: str):
        self._id = id
        self._name = name

    def get_id(self) -> EnergyContainerID:
        return self._id

    def get_component_process_type(self) -> ComponentType:
        return ComponentType.INSTALLATION

    def get_name(self) -> str:
        return self._name

    def is_provider(self) -> bool:
        return False

    def is_fuel_consumer(self) -> bool:
        return False

    def is_electricity_consumer(self) -> bool:
        return False


class InstallationEnergyModel(EnergyModel):
    def __init__(self, id: EnergyContainerID, name: str, fuel_consumers: list[EnergyComponent]):
        self._id = id
        self._name = name
        self._fuel_consumers = {fuel_consumer.get_id(): fuel_consumer for fuel_consumer in fuel_consumers}

    def get_consumers(self, provider_id: str = None) -> list[EnergyContainerID]:
        if provider_id == self._id:
            return list(self._fuel_consumers.keys())
        else:
            return []

    def get_energy_components(self) -> list[EnergyContainerID]:
        return [self._id, *list(self._fuel_consumers.keys())]

    def get_parent(self, container_id: EnergyContainerID) -> EnergyContainerID:
        if container_id in self._fuel_consumers:
            return self._id
        else:
            return None

    def get_root(self) -> EnergyContainerID:
        return self._id

    def get_energy_container(self, container_id: EnergyContainerID) -> EnergyComponent:
        if container_id == self._id:
            return InstallationEnergyContainer(
                id=self._id,
                name=self._name,
            )
        else:
            return self._fuel_consumers[container_id]


@pytest.fixture
def dated_installation_energy_model(
    compressor_system_consumer_dto_fd: FuelConsumerComponent,
    compressor_consumer_dto_fd: FuelConsumerComponent,
) -> EnergyModel:
    return InstallationEnergyModel(
        id=uuid4(),
        name="Installation1",
        fuel_consumers=[compressor_system_consumer_dto_fd, compressor_consumer_dto_fd],
    )
