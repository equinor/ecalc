import yaml

from libecalc.dto import Asset
from libecalc.presentation.yaml.model import PyYamlYamlModel
from libecalc.presentation.yaml.parse_input import map_yaml_to_dto


def ltp_pfs_yaml_factory(
    regularity: float,
) -> Asset:
    input_text = f"""
    START: 2025-01-01
    END: 2030-01-01
    FACILITY_INPUT:
      - NAME: generator_energy_function
        FILE: data/einput/genset_17MW.csv
        TYPE: ELECTRICITY2FUEL
      - NAME: pfs_energy_function
        FILE: data/einput/onshore_power.csv
        TYPE: ELECTRICITY2FUEL
    FUEL_TYPES:
    - NAME: fuel1
      EMISSIONS:
      - NAME: co2
        FACTOR: 2
      - NAME: ch4
        FACTOR: 0.005
      - NAME: nmvoc
        FACTOR: 0.002
      - NAME: nox
        FACTOR: 0.001

    INSTALLATIONS:
    - NAME: minimal_installation
      HCEXPORT: 0
      FUEL: fuel1
      CATEGORY: FIXED
      REGULARITY: {regularity}
      GENERATORSETS:
      - NAME: generator1
        ELECTRICITY2FUEL:
          2025-01-01: generator_energy_function
          2027-01-01: pfs_energy_function
        CATEGORY:
          2025-01-01: TURBINE-GENERATOR
          2027-01-01: POWER-FROM-SHORE
        CABLE_LOSS: 0.2
        MAX_USAGE_FROM_SHORE: 10

        CONSUMERS: # electrical energy consumers
        - NAME: base_load
          CATEGORY: BASE-LOAD
          ENERGY_USAGE_MODEL:
            TYPE: DIRECT
            LOAD: 10


    """

    yaml_text = yaml.safe_load(input_text)
    configuration = PyYamlYamlModel(
        internal_datamodel=yaml_text,
        instantiated_through_read=True,
    )
    yaml_model = map_yaml_to_dto(configuration=configuration, resources={}, name="test")
    return yaml_model
