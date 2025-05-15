import abc
import datetime
import enum
from collections.abc import Iterable
from pathlib import Path
from typing import Any, TextIO

from libecalc.common.logger import logger
from libecalc.presentation.yaml.yaml_entities import (
    ResourceStream,
    YamlTimeseriesResource,
)
from libecalc.presentation.yaml.yaml_keywords import EcalcYamlKeywords
from libecalc.presentation.yaml.yaml_types.components.yaml_asset import YamlAsset
from libecalc.presentation.yaml.yaml_types.components.yaml_installation import YamlInstallation
from libecalc.presentation.yaml.yaml_types.fuel_type.yaml_fuel_type import YamlFuelType
from libecalc.presentation.yaml.yaml_types.models import YamlConsumerModel
from libecalc.presentation.yaml.yaml_types.time_series.yaml_time_series import (
    YamlTimeSeriesCollection,
)
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
    def timeseries_resources(self) -> list[YamlTimeseriesResource]:
        pass

    @property
    @abc.abstractmethod
    def variables(self) -> dict[str, YamlVariable]:
        pass

    @property
    @abc.abstractmethod
    def facility_inputs(self):
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
    def dates(self):
        pass

    @abc.abstractmethod
    def validate(self, context: YamlModelValidationContext) -> YamlAsset: ...


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


class ReaderType(str, enum.Enum):
    """Which yaml model to use. User should in general define capabilities, and get an appropriate yaml model, but for
    now we define implementation.
    """

    RUAMEL = "RUAMEL"  # Conserves comments and horizontal lists, no validation
    PYYAML = "PYYAML"  # Support for validation, does not conserve comments and makes vertical lists


class YamlConfiguration(YamlReader, YamlDumper, metaclass=abc.ABCMeta):
    """Default yaml model specification, that a yaml model implementation
    MUST HAVE reader/loader and dumper/representer behaviour.

    Subclasses of this model MUST have an internal representation of the yaml
    on top level asdict[str, Any]. This is currently in order to have common
    manipulation methods for models that fulfil this criterion. The reason for this
    is that we want all implementations to share a common internal yaml model, that
    is compatible across, but this must be handled and verified properly.
    """

    _internal_datamodel: dict[str, Any] = (
        None  # to temporary store a loaded yaml model. Format is defined by implementation
    )

    def __init__(self, internal_datamodel: dict[str, Any], name: str):
        self._internal_datamodel = internal_datamodel
        self._name = name

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

    class UpdateStatus(enum.Enum):
        """Update status for updating resource files when loading yaml and attempting to match
        To avoid that we just break and raie an exception, but handle it gracefully.

        Inner class, because it is only relevant in this context...
        """

        ZERO_UPDATES = "Zero Updates"
        ONE_UPDATE = "One Update"
        MANY_UPDATES = "Many Updates"

    def update_resource_names(self, mappings: dict[str, str]) -> dict[str, UpdateStatus]:
        """In-place update resource names, mappings on the format:
            old_name: new_name
        :return:
        """
        update_statuses: dict[str, YamlConfiguration.UpdateStatus] = {}

        for old_name, new_name in mappings.items():
            update_statuses[old_name] = self.update_resource_name(old_name, new_name)

        return update_statuses

    def update_resource_name(self, old_name: str, new_name: str) -> UpdateStatus:
        names_updated = 0
        names_updated += self.__update_resource(
            resource_type=EcalcYamlKeywords.time_series,
            field=EcalcYamlKeywords.file,
            old_value=old_name,
            new_value=new_name,
        )
        names_updated += self.__update_resource(
            resource_type=EcalcYamlKeywords.facility_inputs,
            field=EcalcYamlKeywords.file,
            old_value=old_name,
            new_value=new_name,
        )

        names_updated += self.__update_resource(
            resource_type=EcalcYamlKeywords.models,
            field=EcalcYamlKeywords.file,
            old_value=old_name,
            new_value=new_name,
        )

        if names_updated == 0:
            logger.warning(f"No resource was found with name: {old_name}")
            return YamlConfiguration.UpdateStatus.ZERO_UPDATES
        elif names_updated > 1:
            logger.warning(f"More than one resource was updated ({old_name} found {names_updated} times)")
            return YamlConfiguration.UpdateStatus.MANY_UPDATES
        else:
            return YamlConfiguration.UpdateStatus.ONE_UPDATE

    def __update_resource(self, resource_type: str, field: str, old_value: any, new_value: any) -> int:
        """Update a nested dict object in the yaml config data.
        Returns 1 if resource field is found, and 0 if not.
        """
        for resource in self._internal_datamodel.get(resource_type, []):
            try:
                if resource_type == EcalcYamlKeywords.models:
                    if isinstance(resource, dict) and isinstance(
                        resource[EcalcYamlKeywords.consumer_chart_curves], dict
                    ):
                        if resource[EcalcYamlKeywords.consumer_chart_curves][field] == old_value:
                            resource[EcalcYamlKeywords.consumer_chart_curves][field] = new_value
                            return 1
            except KeyError:
                pass
            try:
                if resource[EcalcYamlKeywords.consumer_chart_curve][field] == old_value:
                    resource[EcalcYamlKeywords.consumer_chart_curve][field] = new_value
                    return 1
            except KeyError:
                pass
            try:
                if resource[field] == old_value:
                    resource[field] = new_value
                    return 1
            except KeyError:
                pass

        return 0
