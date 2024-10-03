from io import StringIO
from pathlib import Path
from typing import List

from ecalc_cli.infrastructure.file_resource_service import FileResourceService
from ecalc_cli.types import Frequency
from libecalc.common.utils.rates import RateType
from libecalc.fixtures.cases.ltp_export.ltp_power_from_shore_yaml import OverridableStreamConfigurationService
from libecalc.presentation.yaml.model import YamlModel
from libecalc.presentation.yaml.yaml_entities import ResourceStream


def ltp_oil_loaded_yaml_factory(
    emission_factor: float,
    rate_types: List[RateType],
    fuel_rates: List[float],
    emission_name: str,
    regularity: float,
    categories: List[str],
    consumer_names: List[str],
) -> YamlModel:
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

    configuration_service = OverridableStreamConfigurationService(
        stream=ResourceStream(name="ltp_export", stream=StringIO(input_text))
    )
    resource_service = FileResourceService(working_directory=Path("dummy_path"))

    model = YamlModel(
        configuration_service=configuration_service,
        resource_service=resource_service,
        output_frequency=Frequency.YEAR,
    )
    return model


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
            CONSUMPTION_RATE_TYPE: {rate_type.value}
        """
        consumers = consumers + consumer
    return consumers
