from typing import List

import yaml

from libecalc.common.utils.rates import RateType
from libecalc.dto import Asset
from libecalc.presentation.yaml.model import PyYamlYamlModel
from libecalc.presentation.yaml.parse_input import map_yaml_to_dto


def ltp_oil_loaded_yaml_factory(
    emission_factor: float,
    rate_types: List[RateType],
    fuel_rates: [float],
    emission_name: str,
    regularity: float,
    categories: List[str],
    consumer_names: List[str],
) -> Asset:
    input_text = f"""
    FUEL_TYPES:
    - NAME: fuel
      EMISSIONS:
      - NAME: {emission_name}
        FACTOR: {emission_factor}

    INSTALLATIONS:
    - NAME: minimal_installation
      HCEXPORT: 0
      FUEL: fuel
      CATEGORY: FIXED
      REGULARITY: {regularity}

      FUELCONSUMERS:
      {create_direct_consumers_yaml(categories, fuel_rates, rate_types, consumer_names)}

    """

    create_direct_consumers_yaml(categories, fuel_rates, rate_types, consumer_names)
    yaml_text = yaml.safe_load(input_text)
    configuration = PyYamlYamlModel(
        internal_datamodel=yaml_text,
        instantiated_through_read=True,
    )
    yaml_model = map_yaml_to_dto(configuration=configuration, resources={}, name="test")
    return yaml_model


def create_direct_consumers_yaml(
    categories: List[str], fuel_rates: List[float], rate_types: List[RateType], consumer_names: List[str]
) -> str:
    consumers = ""
    for category, fuel_rate, rate_type, consumer_name in zip(categories, fuel_rates, rate_types, consumer_names):
        consumer = f"""
        - NAME: {consumer_name}
          CATEGORY: {category}
          FUEL: fuel
          ENERGY_USAGE_MODEL:
            TYPE: DIRECT
            FUELRATE: {fuel_rate}
            CONSUMPTION_RATE_TYPE: {rate_type}
        """
        consumers = consumers + consumer
    return consumers
