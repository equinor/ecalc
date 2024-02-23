import abc
import datetime
import enum
from pathlib import Path
from typing import Any, Dict, List, Optional, TextIO, Type

from libecalc.common.logger import logger
from libecalc.presentation.yaml.yaml_entities import (
    ResourceStream,
    YamlTimeseriesResource,
)
from libecalc.presentation.yaml.yaml_keywords import EcalcYamlKeywords
from libecalc.presentation.yaml.yaml_types.components.yaml_asset import YamlAsset
from libecalc.presentation.yaml.yaml_types.yaml_variable import YamlVariable


class YamlValidator(abc.ABC):
    """Validator/parser. For yaml models that understand the eCalc yaml model at a lower level, e.g. has a schema and
    gets details of the model. Currently only PyYaml implementation.
    """

    @abc.abstractmethod
    def facility_resource_names(self) -> List[str]:
        pass

    @abc.abstractmethod
    def timeseries_resources(self) -> List[YamlTimeseriesResource]:
        pass

    @abc.abstractmethod
    def all_resource_names(self) -> List[str]:
        pass

    @abc.abstractmethod
    def variables(self) -> Dict[str, YamlVariable]:
        pass

    @abc.abstractmethod
    def facility_inputs(self):
        pass

    @abc.abstractmethod
    def time_series(self):
        pass

    @abc.abstractmethod
    def models(self):
        pass

    @abc.abstractmethod
    def fuel_types(self):
        pass

    @abc.abstractmethod
    def installations(self):
        pass

    @abc.abstractmethod
    def start(self) -> Optional[datetime.datetime]:
        pass

    @abc.abstractmethod
    def end(self) -> Optional[datetime.datetime]:
        pass

    @abc.abstractmethod
    def dates(self):
        pass

    @abc.abstractmethod
    def validate(self) -> YamlAsset:
        ...


class YamlReader(abc.ABC):
    @classmethod
    @abc.abstractmethod
    def read(
        cls,
        main_yaml: ResourceStream,
        base_dir: Optional[Path] = None,
        resources: Optional[Dict[str, TextIO]] = None,
        enable_include: bool = False,
    ) -> "YamlModel":
        """Named constructor for the yaml model, the way to instantiate the yaml model. We currently
        only allow a yaml model to be constructed by reading a yaml file.

        Either base_dir or resources must be provided. Base_dir is normally used for file-based location (CLI), while
        resources is normally used for cloud-based location (web)

        Further handling of the loaded yaml model must be on the returned instance, which assumes that read() has been run and yaml model has been loaded.

        :param base_dir:    Base directory of the yaml includes and csv resources. All paths must be relative to this dir. Should be/normally parent dir of main yaml.
        :param resources:   List of alternative method to provide yaml includes and csv resources to yaml, directly, through file like objects.
        :param enable_include:  Whether we allow !include syntax in yaml or not.
        :param main_yaml:   The main yaml file, as stream. The only file allowed to have !include and file paths
        :return:    returns an instance of the yamlmodel
        """
        pass


class YamlDumper(abc.ABC):
    @abc.abstractmethod
    def dump(self) -> str:
        """For the given yaml dumper/representer, returns the yaml model as a string
        the way the specific yaml model has been defined to format the data. This
        depends on the type of the yaml model implementation used (e.g. Ruamel, PyYaml) and can currently not be changed.

        :return:    yaml model as a string
        """
        pass


class YamlModelType(str, enum.Enum):
    """Which yaml model to use. User should in general define capabilities, and get an appropriate yaml model, but for
    now we define implementation.
    """

    RUAMEL = "RUAMEL"  # Conserves comments and horizontal lists, no validation
    PYYAML = "PYYAML"  # Support for validation, does not conserve comments and makes vertical lists


class YamlModel(YamlReader, YamlDumper, metaclass=abc.ABCMeta):
    """Default yaml model specification, that a yaml model implementation
    MUST HAVE reader/loader and dumper/representer behaviour.

    Subclasses of this model MUST have an internal representation of the yaml
    on top level as Dict[str, Any]. This is currently in order to have common
    manipulation methods for models that fulfil this criterion. The reason for this
    is that we want all implementations to share a common internal yaml model, that
    is compatible across, but this must be handled and verified properly.
    """

    _internal_datamodel: Dict[
        str, Any
    ] = None  # to temporary store a loaded yaml model. Format is defined by implementation

    def __init__(self, internal_datamodel: Dict[str, Any]):
        self._internal_datamodel = internal_datamodel

    class Builder:
        """Inner class to build yaml models."""

        @staticmethod
        def get_yaml_model(yaml_model_type: YamlModelType) -> Type["YamlModel"]:
            """Note! Returns the type of the YamlModel, and hence NOT an instantiation. That must be
            done later through that type/class's way to do that. (in general through read()).

            :param yaml_model_type:
            :return:
            """
            if yaml_model_type == YamlModelType.RUAMEL:
                # Imported here to avoid circular dependency. The __init__/central module trick didn't work
                from libecalc.presentation.yaml.yaml_models.ruamel_yaml_model import (
                    RuamelYamlModel,
                )

                return RuamelYamlModel
            elif yaml_model_type == YamlModelType.PYYAML:
                from libecalc.presentation.yaml.yaml_models.pyyaml_yaml_model import (
                    PyYamlYamlModel,
                )

                return PyYamlYamlModel

            raise NotImplementedError(f"Unknown yaml model implementation provided: {str(yaml_model_type)}")

    class UpdateStatus(enum.Enum):
        """Update status for updating resource files when loading yaml and attempting to match
        To avoid that we just break and raie an exception, but handle it gracefully.

        Inner class, because it is only relevant in this context...
        """

        ZERO_UPDATES = "Zero Updates"
        ONE_UPDATE = "One Update"
        MANY_UPDATES = "Many Updates"

    def update_resource_names(self, mappings: Dict[str, str]) -> Dict[str, UpdateStatus]:
        """In-place update resource names, mappings on the format:
            old_name: new_name
        :return:
        """
        update_statuses: Dict[str, YamlModel.UpdateStatus] = {}

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
            return YamlModel.UpdateStatus.ZERO_UPDATES
        elif names_updated > 1:
            logger.warning(f"More than one resource was updated ({old_name} found {names_updated} times)")
            return YamlModel.UpdateStatus.MANY_UPDATES
        else:
            return YamlModel.UpdateStatus.ONE_UPDATE

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
