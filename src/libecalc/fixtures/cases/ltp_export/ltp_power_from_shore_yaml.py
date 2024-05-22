from pathlib import Path

import pytest
import yaml

from libecalc.common.time_utils import Frequency
from libecalc.dto import ResultOptions
from libecalc.expression.expression import ExpressionType
from libecalc.fixtures.case_types import DTOCase
from libecalc.presentation.yaml.mappers.variables_mapper import map_yaml_to_variables
from libecalc.presentation.yaml.model import PyYamlYamlModel, YamlModel
from libecalc.presentation.yaml.parse_input import map_yaml_to_dto


@pytest.fixture
def ltp_pfs_yaml_factory():
    def _ltp_pfs_yaml_factory(
        regularity: float,
        cable_loss: ExpressionType,
        max_usage_from_shore: ExpressionType,
        load_direct_consumer: float,
        path: Path,
    ) -> DTOCase:
        input_text = f"""
        START: 2025-01-01
        END: 2030-01-01
        TIME_SERIES:
          - NAME: CABLE_LOSS
            TYPE: DEFAULT
            FILE: data/sim/cable_loss.csv
          - NAME: MAX_USAGE_FROM_SHORE
            TYPE: DEFAULT
            FILE: data/sim/max_usage_from_shore.csv
        FACILITY_INPUTS:
          - NAME: generator_energy_function
            FILE: 'data/einput/genset_17MW.csv'
            TYPE: ELECTRICITY2FUEL
          - NAME: pfs_energy_function
            FILE: 'data/einput/onshore_power.csv'
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
            CABLE_LOSS: {cable_loss}
            MAX_USAGE_FROM_SHORE: {max_usage_from_shore}

            CONSUMERS: # electrical energy consumers
            - NAME: base_load
              CATEGORY: BASE-LOAD
              ENERGY_USAGE_MODEL:
                TYPE: DIRECT
                LOAD: {load_direct_consumer}


        """

        yaml_text = yaml.safe_load(input_text)
        configuration = PyYamlYamlModel(
            internal_datamodel=yaml_text,
            instantiated_through_read=True,
        )

        path = path

        resources = YamlModel._read_resources(yaml_configuration=configuration, working_directory=path)
        variables = map_yaml_to_variables(
            configuration,
            resources=resources,
            result_options=ResultOptions(
                start=configuration.start,
                end=configuration.end,
                output_frequency=Frequency.YEAR,
            ),
        )
        yaml_model = map_yaml_to_dto(configuration=configuration, resources=resources, name="ltp_export")
        return DTOCase(ecalc_model=yaml_model, variables=variables)

    return _ltp_pfs_yaml_factory
