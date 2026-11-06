import abc
import datetime
import enum
from collections.abc import Iterable
from pathlib import Path
from typing import Any, TextIO

from libecalc.presentation.yaml.file_context import FileContext
from libecalc.presentation.yaml.yaml_entities import (
    ResourceStream,
)
from libecalc.presentation.yaml.yaml_models.yaml_editable import DataModelYamlEditor, YamlEditable
from libecalc.presentation.yaml.yaml_types.components.yaml_asset import YamlAsset, YamlDefinitions
from libecalc.presentation.yaml.yaml_types.components.yaml_installation import YamlInstallation
from libecalc.presentation.yaml.yaml_types.energy.yaml_energy_network import YamlEnergyNetwork
from libecalc.presentation.yaml.yaml_types.facility_model.yaml_facility_model import YamlFacilityModel
from libecalc.presentation.yaml.yaml_types.fuel_type.yaml_fuel_type import YamlFuelType
from libecalc.presentation.yaml.yaml_types.models import YamlConsumerModel, YamlFluidModel
from libecalc.presentation.yaml.yaml_types.process.yaml_process_pipeline import YamlProcessPipeline
from libecalc.presentation.yaml.yaml_types.process.yaml_process_simulation import (
    YamlEcalcEvent,
    YamlEnergyEvent,
    YamlProcessEvent,
    YamlProcessSimulation,
    YamlPumpProcessSimulation,
)
from libecalc.presentation.yaml.yaml_types.streams.yaml_inlet_stream import YamlInletStream
from libecalc.presentation.yaml.yaml_types.time_series.yaml_time_series import (
    YamlTimeSeriesCollection,
)
from libecalc.presentation.yaml.yaml_types.yaml_compressor import YamlCompressor
from libecalc.presentation.yaml.yaml_types.yaml_shaft import YamlShaft
from libecalc.presentation.yaml.yaml_types.yaml_variable import YamlVariable
from libecalc.presentation.yaml.yaml_validation_context import (
    YamlModelValidationContext,
)


class YamlValidator(abc.ABC):
    """Validator/parser. For yaml models that understand the eCalc yaml model at a lower level, e.g. has a schema and
    gets details of the model. Currently only PyYaml implementation.
    """

    @property
    @abc.abstractmethod
    def name(self) -> str: ...

    @property
    @abc.abstractmethod
    def facility_resource_names(self) -> list[str]:
        pass

    @property
    @abc.abstractmethod
    def timeseries_resource_names(self) -> list[str]:
        pass

    @property
    @abc.abstractmethod
    def variables(self) -> dict[str, YamlVariable]:
        pass

    @property
    @abc.abstractmethod
    def facility_inputs(self) -> list[YamlFacilityModel]:
        pass

    @property
    @abc.abstractmethod
    def time_series(self) -> list[YamlTimeSeriesCollection]:
        pass

    @property
    @abc.abstractmethod
    def models(self) -> Iterable[YamlConsumerModel]:
        pass

    @property
    @abc.abstractmethod
    def fuel_types(self) -> Iterable[YamlFuelType]:
        pass

    @property
    @abc.abstractmethod
    def fluid_models(self) -> dict[str, YamlFluidModel]:
        pass

    @property
    @abc.abstractmethod
    def inlet_streams(self) -> dict[str, YamlInletStream]:
        pass

    @property
    @abc.abstractmethod
    def definitions(self) -> YamlDefinitions:
        pass

    @property
    @abc.abstractmethod
    def shafts(self) -> list[YamlShaft]:
        pass

    @property
    @abc.abstractmethod
    def compressors(self) -> list[YamlCompressor]:
        pass

    @property
    @abc.abstractmethod
    def process_pipelines(self) -> dict[str, YamlProcessPipeline]:
        pass

    @property
    @abc.abstractmethod
    def process_simulations(self) -> Iterable[YamlProcessSimulation]:
        pass

    @property
    @abc.abstractmethod
    def energy_network(self) -> YamlEnergyNetwork | None:
        pass

    @property
    @abc.abstractmethod
    def ecalc_events(self) -> list[YamlEcalcEvent]:
        pass

    @property
    @abc.abstractmethod
    def process_events(self) -> list[YamlProcessEvent]:
        pass

    @property
    @abc.abstractmethod
    def energy_events(self) -> list[YamlEnergyEvent]:
        pass

    @property
    @abc.abstractmethod
    def pump_process_simulations(self) -> Iterable[YamlPumpProcessSimulation]:
        pass

    @property
    @abc.abstractmethod
    def installations(self) -> Iterable[YamlInstallation]:
        pass

    @property
    @abc.abstractmethod
    def start(self) -> datetime.datetime | None:
        pass

    @property
    @abc.abstractmethod
    def end(self) -> datetime.datetime | None:
        pass

    @property
    @abc.abstractmethod
    def dates(self) -> list[datetime.datetime]:
        pass

    @abc.abstractmethod
    def validate(self, context: YamlModelValidationContext) -> YamlAsset: ...

    @abc.abstractmethod
    def get_file_context(self, yaml_path: tuple[str | int | datetime.datetime, ...]) -> FileContext | None: ...


class YamlReader(abc.ABC):
    @classmethod
    @abc.abstractmethod
    def read(
        cls,
        main_yaml: ResourceStream,
        base_dir: Path | None = None,
        resources: dict[str, TextIO] | None = None,
        enable_include: bool = False,
    ) -> "YamlConfiguration":
        """Named constructor for the yaml model, the way to instantiate the yaml model. We currently
        only allow a yaml model to be constructed by reading a yaml file.

        Either base_dir or resources must be provided. Base_dir is normally used for file-based location (CLI), while
        resources is normally used for cloud-based location (web)

        Further handling of the loaded yaml model must be on the returned instance, which assumes that read() has been run and yaml model has been loaded.

        :param base_dir:    Base directory of the yaml includes and csv resources. All paths must be relative to this dir. Should be/normally parent dir of main yaml.
        :param resources:  list of alternative method to provide yaml includes and csv resources to yaml, directly, through file like objects.
        :param enable_include:  Whether we allow !include syntax in yaml or not.
        :param main_yaml:   The main yaml file, as stream. The only file allowed to have !include and file paths
        :return:    returns an instance of the yamlmodel
        """
        pass

    @classmethod
    @abc.abstractmethod
    def get_validator(
        cls,
        main_yaml: ResourceStream,
        base_dir: Path | None = None,
        resources: dict[str, TextIO] | None = None,
        enable_include: bool = False,
    ) -> "YamlValidator": ...

    """
    Get yaml validator
    """


class YamlDumper(abc.ABC):
    @abc.abstractmethod
    def dump(self) -> str:
        """For the given yaml dumper/representer, returns the yaml model as a string
        the way the specific yaml model has been defined to format the data. This
        depends on the type of the yaml model implementation used (e.g. Ruamel, PyYaml) and can currently not be changed.

        :return:    yaml model as a string
        """
        pass


class ReaderType(enum.StrEnum):
    """Which yaml model to use. User should in general define capabilities, and get an appropriate yaml model, but for
    now we define implementation.
    """

    RUAMEL = "RUAMEL"  # Conserves comments and horizontal lists, no validation
    PYYAML = "PYYAML"  # Support for validation, does not conserve comments and makes vertical lists


class YamlConfiguration(YamlReader, YamlDumper, metaclass=abc.ABCMeta):
    """Default YAML model specification, that a YAML model implementation
    MUST HAVE reader/loader and dumper/representer behavior.

    Subclasses of this model MUST have an internal representation of the YAML
    on top level asdict[str, Any]. This is currently in order to have common
    manipulation methods for models that fulfil this criterion. The reason for this
    is that we want all implementations to share a common internal YAML model that
    is compatible across, but this must be handled and verified properly.
    """

    # To temporary store a loaded YAML model. Format is defined by implementation.
    _internal_datamodel: dict[str, Any] = {}

    def __init__(self, internal_datamodel: dict[str, Any], name: str):
        self._internal_datamodel = internal_datamodel
        self._name = name

    def as_editable(self) -> YamlEditable:
        """Get an editor for this yaml model. Edits are applied in place, and are reflected when dumping the model."""
        return DataModelYamlEditor(self._internal_datamodel)

    class Builder:
        """Inner class to build yaml models."""

        @staticmethod
        def get_yaml_reader(reader_type: ReaderType) -> type["YamlReader"]:
            """Note! Returns the type of the YamlModel, and hence NOT an instantiation. That must be
            done later through that type/class's way to do that. (in general through read()).

            :param reader_type:
            :return:
            """
            if reader_type == ReaderType.RUAMEL:
                # Imported here to avoid circular dependency. The __init__/central module trick didn't work
                from libecalc.presentation.yaml.yaml_models.ruamel_yaml_model import (
                    RuamelYamlModel,
                )

                return RuamelYamlModel
            elif reader_type == ReaderType.PYYAML:
                from libecalc.presentation.yaml.yaml_models.pyyaml_yaml_model import (
                    PyYamlYamlModel,
                )

                return PyYamlYamlModel

            raise NotImplementedError(f"Unknown yaml model implementation provided: {str(reader_type)}")
