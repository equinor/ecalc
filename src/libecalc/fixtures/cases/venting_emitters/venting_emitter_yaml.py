import yaml

from libecalc.common.units import Unit
from libecalc.common.utils.rates import RateType
from libecalc.dto import Asset
from libecalc.presentation.yaml.model import PyYamlYamlModel
from libecalc.presentation.yaml.parse_input import map_yaml_to_dto


def venting_emitter_yaml_factory(
    emission_rate: float, rate_type: RateType, unit: Unit, emission_name: str, regularity: float
) -> Asset:
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

      VENTING_EMITTERS:
      - NAME: Venting emitter 1
        CATEGORY: COLD-VENTING-FUGITIVE
        EMISSION:
          NAME: {emission_name}
          RATE:
            VALUE: {emission_rate}
            UNIT: {unit}
            TYPE: {rate_type}

    """

    yaml_text = yaml.safe_load(input_text)
    configuration = PyYamlYamlModel(
        internal_datamodel=yaml_text,
        instantiated_through_read=True,
    )
    yaml_model = map_yaml_to_dto(configuration=configuration, resources={}, name="test")
    return yaml_model
