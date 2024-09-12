from io import StringIO
from pathlib import Path
from typing import List

from ecalc_cli.infrastructure.file_resource_service import FileResourceService
from libecalc.common.time_utils import Frequency
from libecalc.common.units import Unit
from libecalc.common.utils.rates import RateType
from libecalc.fixtures.case_types import DTOCase
from libecalc.presentation.yaml.model import YamlModel
from libecalc.presentation.yaml.yaml_entities import ResourceStream
from libecalc.presentation.yaml.yaml_types.emitters.yaml_venting_emitter import (
    YamlVentingType,
)
from libecalc.presentation.yaml.yaml_types.yaml_stream_conditions import (
    YamlEmissionRateUnits,
    YamlOilRateUnits,
)
from tests.libecalc.input.mappers.test_model_mapper import OverridableStreamConfigurationService


def venting_emitter_yaml_factory(
    rate_types: List[RateType],
    units: List[YamlEmissionRateUnits],
    emission_names: List[str],
    regularity: float,
    names: List[str],
    path: Path,
    emission_rates: List[float] = None,
    emitter_types: List[str] = None,
    categories: List[str] = None,
    emission_keyword_name: str = "EMISSIONS",
    installation_name: str = "minimal_installation",
    emission_factors: List[float] = None,
    oil_rates: List[float] = None,
    units_oil_rates: List[YamlOilRateUnits] = None,
    include_emitters: bool = True,
    include_fuel_consumers: bool = True,
) -> DTOCase:
    if categories is None:
        categories = ["STORAGE"] * len(names)
    if emitter_types is None:
        emitter_types = ["DIRECT_EMISSION"] * len(names)
    if emission_factors is None:
        emission_factors = [0.1] * len(emission_names)
    if oil_rates is None:
        oil_rates = [10] * len(names)
    if units_oil_rates is None:
        units_oil_rates = [Unit.KILO_PER_DAY] * len(names)
    if emission_rates is None:
        emission_rates = [10] * len(names)

    input_text = f"""
        FACILITY_INPUTS:
          - NAME: generator_energy_function
            FILE: '../ltp_export/data/einput/genset_17MW.csv'
            TYPE: ELECTRICITY2FUEL
        FUEL_TYPES:
        - NAME: fuel
          EMISSIONS:
          - NAME: co2
            FACTOR: 2

        START: 2027-01-01
        END: 2029-01-01

        INSTALLATIONS:
        - NAME: {installation_name}
          HCEXPORT: 0
          FUEL: fuel
          CATEGORY: FIXED
          REGULARITY: {regularity}

            {create_fuel_consumers(include_fuel_consumers=include_fuel_consumers,)}

          {create_venting_emitters_yaml(
        categories=categories, rate_types=rate_types, emitter_names=names, emission_names=emission_names,
        emission_rates=emission_rates, units=units, emission_keyword_name=emission_keyword_name, include_emitters=include_emitters,
        emitter_types=emitter_types, oil_rates=oil_rates, emission_factors=emission_factors, units_oil_rates=units_oil_rates,
    )}

        """

    configuration_service = OverridableStreamConfigurationService(
        stream=ResourceStream(
            name="venting_emitters",
            stream=StringIO(input_text),
        )
    )
    resource_service = FileResourceService(working_directory=path)
    model = YamlModel(
        configuration_service=configuration_service, resource_service=resource_service, output_frequency=Frequency.YEAR
    )

    return DTOCase(ecalc_model=model.dto, variables=model.variables)


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
    units: List[YamlEmissionRateUnits],
    units_oil_rates: List[YamlOilRateUnits],
    emission_keyword_name: str,
    emission_factors: List[float],
    oil_rates: List[float],
    include_emitters: bool,
    emitter_types: List[str],
) -> str:
    if not include_emitters:
        return ""
    else:
        emitters = "VENTING_EMITTERS:"
        for category, rate_type, emitter_name, emitter_type, oil_rate, unit_oil_rate in zip(
            categories,
            rate_types,
            emitter_names,
            emitter_types,
            oil_rates,
            units_oil_rates,
        ):
            emissions = ""
            if emitter_type == YamlVentingType.DIRECT_EMISSION.name:
                emission_keyword = emission_keyword_name
                for emission_name, emission_rate, unit in zip(emission_names, emission_rates, units):
                    emission = f"""
                    - NAME: {emission_name}
                      RATE:
                        VALUE: {emission_rate}
                        UNIT:  {unit.value if isinstance(unit, YamlEmissionRateUnits) else unit}
                        TYPE: {rate_type.value}
                    """
                    emissions = emissions + emission
            else:
                emission_keyword = "VOLUME"
                emissions = f"""
                RATE:
                  VALUE: {oil_rate}
                  UNIT: {unit_oil_rate.value}
                  TYPE: {rate_type.value}
                EMISSIONS:
                """
                for emission_name, emission_factor in zip(emission_names, emission_factors):
                    emission = f"""
                    - NAME: {emission_name}
                      EMISSION_FACTOR: {emission_factor}
                    """
                    emissions = emissions + emission

            emitter = f"""
            - NAME: {emitter_name}
              CATEGORY: {category}
              TYPE: {emitter_type}
              {emission_keyword}:
                {emissions}
            """
            emitters = emitters + emitter
    return emitters
