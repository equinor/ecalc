from typing import List

import yaml

from libecalc.common.units import Unit
from libecalc.common.utils.rates import RateType
from libecalc.dto import Asset
from libecalc.presentation.yaml.model import PyYamlYamlModel
from libecalc.presentation.yaml.parse_input import map_yaml_to_dto


def venting_emitter_yaml_factory(
    emission_rates: List[float],
    rate_types: List[RateType],
    units: List[Unit],
    emission_names: List[str],
    regularity: float,
    volume_factors: List[float] = None,
    categories: List[str] = None,
    emission_keyword_name: str = "EMISSION",
    names: List[str] = None,
    include_emitters: bool = True,
    include_fuel_consumers: bool = True,
) -> Asset:
    if categories is None:
        categories = ["STORAGE"]
    if names is None:
        names = ["Venting emitter 1"]
    if volume_factors is None:
        volume_factors = [None]

    input_text = f"""
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
          CATEGORY: FIXED
          REGULARITY: {regularity}

            {create_fuel_consumers(include_fuel_consumers=include_fuel_consumers,)}

          {create_venting_emitters_yaml(
        categories=categories, rate_types=rate_types, emitter_names=names, emission_names=emission_names,
        emission_rates=emission_rates, units=units, emission_keyword_name=emission_keyword_name, include_emitters=include_emitters,
        volume_factors=volume_factors,
    )}

        """

    create_fuel_consumers(include_fuel_consumers=include_fuel_consumers)

    create_venting_emitters_yaml(
        categories=categories,
        rate_types=rate_types,
        emitter_names=names,
        emission_names=emission_names,
        emission_rates=emission_rates,
        units=units,
        volume_factors=volume_factors,
        emission_keyword_name=emission_keyword_name,
        include_emitters=include_emitters,
    )
    yaml_text = yaml.safe_load(input_text)
    configuration = PyYamlYamlModel(
        internal_datamodel=yaml_text,
        instantiated_through_read=True,
    )
    yaml_model = map_yaml_to_dto(configuration=configuration, resources={}, name="test")
    return yaml_model


def create_fuel_consumers(include_fuel_consumers: bool) -> str:
    if not include_fuel_consumers:
        return ""
    else:
        fuel_consumers = """
          FUELCONSUMERS:
          - NAME: Fuel consumer 1
            CATEGORY: MISCELLANEOUS
            FUEL: fuel
            ENERGY_USAGE_MODEL:
              TYPE: DIRECT
              FUELRATE: 10
        """
    return fuel_consumers


def create_venting_emitters_yaml(
    categories: List[str],
    rate_types: List[RateType],
    emitter_names: List[str],
    emission_names: List[str],
    emission_rates: List[float],
    units: List[Unit],
    volume_factors: List[float],
    emission_keyword_name: str,
    include_emitters: bool,
) -> str:
    if not include_emitters:
        return ""
    else:
        emitters = "VENTING_EMITTERS:"
        for category, rate_type, emitter_name, emission_name, emission_rate, unit, volume_factor in zip(
            categories,
            rate_types,
            emitter_names,
            emission_names,
            emission_rates,
            units,
            volume_factors,
        ):
            volume_factor_string = (
                f"EMISSION_RATE_TO_VOLUME_FACTOR: {volume_factor}" if volume_factor is not None else ""
            )
            emitter = f"""
            - NAME: {emitter_name}
              CATEGORY: {category}
              {emission_keyword_name}:
                NAME: {emission_name}
                {volume_factor_string}
                RATE:
                  VALUE: {emission_rate}
                  UNIT:  {unit}
                  TYPE: {rate_type}
            """
            emitters = emitters + emitter
    return emitters
