import datetime

import pytest
from libecalc import dto
from libecalc.dto.base import ComponentType
from libecalc.expression import Expression
from libecalc.presentation.flow_diagram.fde_models import Flow, FlowType, Node, NodeType

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


def compressor_system_compressor_fd(name: str) -> dto.CompressorSystemCompressor:
    """Create a compressor system, only relevant property is the name when used to generate a FlowDiagram
    :param name:
    :return:
    """
    return dto.CompressorSystemCompressor(
        name=name,
        compressor_train=dto.CompressorSampled(
            energy_usage_values=[0, 4500, 9500],
            rate_values=[0, 5000, 10000],
            suction_pressure_values=[5, 5, 5],
            discharge_pressure_values=[50, 50, 50],
            energy_usage_type=dto.types.EnergyUsageType.FUEL,
            energy_usage_adjustment_constant=0,
            energy_usage_adjustment_factor=1.0,
        ),
    )


@pytest.fixture
def fuel_type_fd() -> dto.types.FuelType:
    return dto.types.FuelType(
        name="fuel_gas",
        price=Expression.setup_from_expression(value="1.5"),
        emissions=[
            dto.Emission(
                name="co2",
                factor=Expression.setup_from_expression(value="2.20"),
                tax=Expression.setup_from_expression(value="1.51"),
            )
        ],
    )


@pytest.fixture
def compressor_system_consumer_dto_fd(fuel_type_fd) -> dto.FuelConsumer:
    return dto.FuelConsumer(
        name="Compressor system 1",
        component_type=ComponentType.COMPRESSOR_SYSTEM,
        user_defined_category={datetime.datetime(1900, 1, 1): "COMPRESSOR"},
        fuel={datetime.datetime(1900, 1, 1): fuel_type_fd},
        regularity={datetime.datetime(1900, 1, 1): Expression.setup_from_expression(1)},
        energy_usage_model={
            datetime.datetime(2018, 1, 1): dto.CompressorSystemConsumerFunction(
                energy_usage_type=dto.types.EnergyUsageType.FUEL,
                compressors=[
                    compressor_system_compressor_fd("compressor1"),
                    compressor_system_compressor_fd("compressor2"),
                ],
                total_system_rate=Expression.setup_from_expression(value="5"),
                operational_settings=[
                    dto.CompressorSystemOperationalSetting(
                        rate_fractions=[
                            Expression.setup_from_expression(value=1),
                            Expression.setup_from_expression(value=0),
                        ],
                        suction_pressures=[
                            Expression.setup_from_expression(value=3),
                            Expression.setup_from_expression(value=3),
                        ],
                        discharge_pressures=[
                            Expression.setup_from_expression(value=200),
                            Expression.setup_from_expression(value=200),
                        ],
                    ),
                    dto.CompressorSystemOperationalSetting(
                        rate_fractions=[
                            Expression.setup_from_expression(value=0.5),
                            Expression.setup_from_expression(value=0.5),
                        ],
                        suction_pressure=Expression.setup_from_expression(value=3),
                        discharge_pressure=Expression.setup_from_expression(value=200),
                    ),
                ],
            ),
            datetime.datetime(2020, 1, 1): dto.CompressorSystemConsumerFunction(
                energy_usage_type=dto.types.EnergyUsageType.FUEL,
                compressors=[
                    compressor_system_compressor_fd("compressor1"),
                    compressor_system_compressor_fd("compressor2"),
                    compressor_system_compressor_fd("compressor3"),
                ],
                total_system_rate=Expression.setup_from_expression(value="5"),
                operational_settings=[
                    dto.CompressorSystemOperationalSetting(
                        rate_fractions=[
                            Expression.setup_from_expression(value=1),
                            Expression.setup_from_expression(value=0),
                            Expression.setup_from_expression(value=0),
                        ],
                        suction_pressures=[
                            Expression.setup_from_expression(value=3),
                            Expression.setup_from_expression(value=3),
                            Expression.setup_from_expression(value=3),
                        ],
                        discharge_pressures=[
                            Expression.setup_from_expression(value=200),
                            Expression.setup_from_expression(value=200),
                            Expression.setup_from_expression(value=200),
                        ],
                    ),
                    dto.CompressorSystemOperationalSetting(
                        rate_fractions=[
                            Expression.setup_from_expression(value=0.33),
                            Expression.setup_from_expression(value=0.33),
                            Expression.setup_from_expression(value=0.34),
                        ],
                        suction_pressure=Expression.setup_from_expression(value=3),
                        discharge_pressure=Expression.setup_from_expression(value=200),
                    ),
                ],
            ),
        },
    )


@pytest.fixture
def compressor_consumer_dto_fd(fuel_type_fd) -> dto.FuelConsumer:
    return dto.FuelConsumer(
        name="Compressor 1",
        component_type=ComponentType.GENERIC,
        user_defined_category={datetime.datetime(1900, 1, 1): "COMPRESSOR"},
        fuel={datetime.datetime(1900, 1, 1): fuel_type_fd},
        energy_usage_model={
            datetime.datetime(2019, 1, 1): dto.DirectConsumerFunction(
                fuel_rate=Expression.setup_from_expression(value=5), energy_usage_type=dto.types.EnergyUsageType.FUEL
            )
        },
        regularity={datetime.datetime(1900, 1, 1): Expression.setup_from_expression(1)},
    )


@pytest.fixture
def installation_with_dates_dto_fd(
    compressor_system_consumer_dto_fd: dto.FuelConsumer,
    compressor_consumer_dto_fd: dto.FuelConsumer,
) -> dto.Asset:
    return dto.Asset(
        name="installation_with_dates",
        installations=[
            dto.Installation(
                name="Installation1",
                fuel_consumers=[compressor_system_consumer_dto_fd, compressor_consumer_dto_fd],
                regularity={datetime.datetime(1900, 1, 1): Expression.setup_from_expression(1)},
                hydrocarbon_export={datetime.datetime(1900, 1, 1): Expression.setup_from_expression(0)},
            )
        ],
    )
