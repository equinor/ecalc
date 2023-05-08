from typing import NamedTuple

import pytest


class YamlModel(NamedTuple):
    name: str
    source: str


@pytest.fixture
def minimal_model_yaml_factory():
    def minimal_model_yaml(fuel_rate: int = 50):
        return YamlModel(
            name="minimal_model",
            source=f"""
FUEL_TYPES:
  - NAME: fuel
    EMISSIONS:
      - NAME: co2
        FACTOR: 2

START: 2020-01-01
END: 2023-01-01

INSTALLATIONS:
  - NAME: minimal_installation
    HCEXPORT: 0
    FUEL: fuel
    FUELCONSUMERS:
      - NAME: direct
        CATEGORY: MISCELLANEOUS
        ENERGY_USAGE_MODEL:
          TYPE: DIRECT
          FUELRATE: {fuel_rate}
""",
        )

    return minimal_model_yaml
