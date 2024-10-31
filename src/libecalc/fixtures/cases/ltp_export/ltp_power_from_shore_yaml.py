from io import StringIO
from pathlib import Path
from typing import Optional, cast

import pytest

from ecalc_cli.infrastructure.file_resource_service import FileResourceService
from libecalc.common.time_utils import Frequency
from libecalc.expression.expression import ExpressionType
from libecalc.fixtures.case_types import DTOCase
from libecalc.presentation.yaml.configuration_service import ConfigurationService
from libecalc.presentation.yaml.model import YamlModel
from libecalc.presentation.yaml.yaml_entities import ResourceStream
from libecalc.presentation.yaml.yaml_models.yaml_model import ReaderType, YamlConfiguration, YamlValidator


class OverridableStreamConfigurationService(ConfigurationService):
    def __init__(self, stream: ResourceStream, overrides: Optional[dict] = None):
        self._overrides = overrides
        self._stream = stream

    def get_configuration(self) -> YamlValidator:
        main_yaml_model = YamlConfiguration.Builder.get_yaml_reader(ReaderType.PYYAML).read(
            main_yaml=self._stream,
            enable_include=True,
        )

        if self._overrides is not None:
            main_yaml_model._internal_datamodel.update(self._overrides)
        return cast(YamlValidator, main_yaml_model)


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
        END: 2031-01-01
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

        configuration_service = OverridableStreamConfigurationService(
            stream=ResourceStream(name="ltp_export", stream=StringIO(input_text))
        )
        resource_service = FileResourceService(working_directory=path)

        model = YamlModel(
            configuration_service=configuration_service,
            resource_service=resource_service,
            output_frequency=Frequency.YEAR,
        )

        return DTOCase(ecalc_model=model.dto, variables=model.variables)

    return _ltp_pfs_yaml_factory
