from datetime import datetime

import pytest

from libecalc.common.component_type import ComponentType
from libecalc.common.energy_usage_type import EnergyUsageType
from libecalc.common.time_utils import Period
from libecalc.dto import Asset, DirectConsumerFunction, Emission, FuelConsumer, FuelType, Installation
from libecalc.dto.types import ConsumerUserDefinedCategoryType, InstallationUserDefinedCategoryType
from libecalc.expression import Expression


def minimal_installation_dto(
    installation_name: str = "minimal_installation", fuel_rate: int = 50, start: datetime = datetime(2020, 1, 1)
):
    regularity = {Period(start): Expression.setup_from_expression(1)}
    return Installation(
        name=installation_name,
        regularity=regularity,
        venting_emitters=[],
        hydrocarbon_export={Period(start): Expression.setup_from_expression(0)},
        user_defined_category=InstallationUserDefinedCategoryType.FIXED,
        fuel_consumers=[
            FuelConsumer(
                name=f"{installation_name}-direct",
                component_type=ComponentType.GENERIC,
                user_defined_category={Period(start): ConsumerUserDefinedCategoryType.MISCELLANEOUS},
                regularity=regularity,
                fuel={
                    Period(start): FuelType(
                        name="fuel",
                        emissions=[
                            Emission(
                                name="co2",
                                factor=Expression.setup_from_expression(2),
                            )
                        ],
                    )
                },
                energy_usage_model={
                    Period(start): DirectConsumerFunction(
                        fuel_rate=Expression.setup_from_expression(fuel_rate),
                        energy_usage_type=EnergyUsageType.FUEL,
                    )
                },
            )
        ],
    )


@pytest.fixture
def minimal_installation_dto_factory():
    return minimal_installation_dto


@pytest.fixture
def minimal_model_dto_factory():
    def minimal_model_dto(
        asset_name: str = "minimal_model", fuel_rate: int = 50, start: datetime = datetime(2020, 1, 1)
    ):
        return Asset(
            name=asset_name,
            installations=[minimal_installation_dto(fuel_rate=fuel_rate, start=start)],
        )

    return minimal_model_dto
