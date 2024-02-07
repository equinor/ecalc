import datetime
import re
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, TextIO, Type, Union

import yaml
from pydantic import TypeAdapter
from pydantic import ValidationError as PydanticValidationError
from typing_extensions import Self
from yaml import SafeLoader

from libecalc.common.errors.exceptions import EcalcError, ProgrammingError
from libecalc.common.time_utils import convert_date_to_datetime
from libecalc.dto.utils.validators import (
    COMPONENT_NAME_ALLOWED_CHARS,
    COMPONENT_NAME_PATTERN,
)
from libecalc.presentation.yaml.validation_errors import (
    DataValidationError,
    DtoValidationError,
    DumpFlowStyle,
    ValidationError,
)
from libecalc.presentation.yaml.yaml_entities import (
    ResourceStream,
    YamlDict,
    YamlList,
    YamlTimeseriesResource,
    YamlTimeseriesType,
)
from libecalc.presentation.yaml.yaml_keywords import EcalcYamlKeywords
from libecalc.presentation.yaml.yaml_models.yaml_model import YamlModel, YamlValidator
from libecalc.presentation.yaml.yaml_types.components.yaml_asset import YamlAsset
from libecalc.presentation.yaml.yaml_types.time_series.yaml_time_series import (
    YamlTimeSeriesCollection,
)
from libecalc.presentation.yaml.yaml_types.yaml_variable import (
    YamlVariableReferenceId,
    YamlVariables,
)


class PyYamlYamlModel(YamlValidator, YamlModel):
    """Implementation of yaml model using PyYaml library
    Keeping comments and horizontal lists on loading currently not supported!
    """

    def __init__(self, internal_datamodel: Dict[str, Any], instantiated_through_read: bool = False):
        """To avoid mistakes, make sure that this is only instantiated through read method/named constructor
        :param instantiated_through_read: set to True to allow to use constructor.
        """
        if not instantiated_through_read:
            raise ProgrammingError(f"{self.__class__} can only be instantiated through read() method/named constructor")

        super().__init__(internal_datamodel=internal_datamodel)

    def dump(self) -> str:
        if self._internal_datamodel is None:
            raise ProgrammingError("You cannot dump a model without first reading one. Use read() to read a model.")

        return PyYamlYamlModel.dump_yaml(self._internal_datamodel)

    @classmethod
    def read(
        cls,
        main_yaml: ResourceStream,
        base_dir: Optional[Path] = None,
        resources: Optional[Dict[str, TextIO]] = None,
        enable_include: bool = True,
    ) -> "PyYamlYamlModel":
        internal_datamodel = PyYamlYamlModel.read_yaml(
            main_yaml=main_yaml, resources=resources, base_dir=base_dir, enable_include=enable_include
        )
        self = cls(internal_datamodel=internal_datamodel, instantiated_through_read=True)
        return self

    class SafeLineLoader(SafeLoader):
        def construct_yaml_map(self, node):
            (obj,) = super().construct_yaml_map(node)
            return YamlDict(obj, start_mark=node.start_mark, end_mark=node.end_mark)

        def construct_yaml_seq(self, node):
            (obj,) = super().construct_yaml_seq(node)
            return YamlList(obj, start_mark=node.start_mark, end_mark=node.end_mark)

    SafeLineLoader.add_constructor("tag:yaml.org,2002:map", SafeLineLoader.construct_yaml_map)

    SafeLineLoader.add_constructor("tag:yaml.org,2002:seq", SafeLineLoader.construct_yaml_seq)

    class IncludeConstructor:
        """Add !include constructor to the yaml reader.
        This will include a separate yaml file into the position where the include keyword is placed.

        Example:
            SOME_KEY: !include some.yaml
        """

        def __init__(self, base_dir: Optional[Path] = None, resources: Optional[Dict[str, TextIO]] = None):
            self._base_dir = base_dir
            self._resources = resources if resources else {}

        def __call__(self, loader: yaml.SafeLoader, node: yaml.ScalarNode):
            resource_name = str(loader.construct_scalar(node=node))
            if self._resources:
                yaml_resource = ResourceStream(stream=self._resources[resource_name], name=resource_name)
                yaml_data = PyYamlYamlModel._read_yaml_helper(
                    yaml_file=yaml_resource, resources=self._resources, loader=loader.__class__, enable_include=True
                )
            elif self._base_dir:
                resource_path = self._base_dir / str(resource_name)
                with open(resource_path) as resource_file:
                    yaml_resource = ResourceStream(name=resource_path.name, stream=resource_file)
                    yaml_data = PyYamlYamlModel._read_yaml_helper(
                        yaml_file=yaml_resource, loader=loader.__class__, enable_include=True, base_dir=self._base_dir
                    )
            else:
                raise ValueError(
                    f"Could not find the !include resource: {resource_name} in either attached resources nor bas_dir."
                )
            return yaml_data

    class IndentationDumper(yaml.Dumper):
        """In order to increase indentation of nested elements."""

        def increase_indent(self, flow=False, indentless=False):
            return super(PyYamlYamlModel.IndentationDumper, self).increase_indent(flow, False)

    class YamlReader:
        def __init__(
            self,
            loader: Type[yaml.SafeLoader],
            enable_include: bool = True,
            base_dir: Optional[Path] = None,
            resources: Optional[Dict[str, TextIO]] = None,
        ):
            self.__loader = loader
            if enable_include and (base_dir or resources):
                loader.add_constructor(
                    "!include",
                    PyYamlYamlModel.IncludeConstructor(base_dir=base_dir, resources=resources),
                )

        def load(self, yaml_file: ResourceStream):
            if re.search(COMPONENT_NAME_PATTERN, Path(yaml_file.name).stem) is None:
                raise EcalcError(
                    title="Bad Yaml file name",
                    message=f"The model file, {yaml_file.name}, contains illegal special characters. "
                    f"Allowed characters are {COMPONENT_NAME_ALLOWED_CHARS}",
                )
            try:
                return yaml.load(yaml_file, Loader=self.__loader)  # noqa: S506 - loader should be SafeLoader
            except KeyError as e:
                raise EcalcError(
                    title="Bad Yaml file", message=f"Error occurred while loading yaml file, key {e} not found"
                ) from e

        def dump_and_load(self, yaml_file: ResourceStream):
            return yaml.dump(self.load(yaml_file), Dumper=PyYamlYamlModel.IndentationDumper, sort_keys=False)

    @staticmethod
    def _read_yaml_helper(
        yaml_file: ResourceStream,
        loader: Type[yaml.SafeLoader],
        enable_include: bool = True,
        base_dir: Optional[Path] = None,
        resources: Optional[Dict[str, TextIO]] = None,
    ):
        """Read yaml helper for include functionality."""
        yaml_reader = PyYamlYamlModel.YamlReader(
            loader=loader, enable_include=enable_include, base_dir=base_dir, resources=resources
        )
        return yaml_reader.load(yaml_file)

    @staticmethod
    def dump_and_load_yaml(
        main_yaml: ResourceStream,
        enable_include: bool = True,
        base_dir: Optional[Path] = None,
        resources: Optional[Dict[str, TextIO]] = None,
    ) -> str:
        yaml_reader = PyYamlYamlModel.YamlReader(
            loader=SafeLoader, enable_include=enable_include, base_dir=base_dir, resources=resources
        )
        return yaml_reader.dump_and_load(main_yaml)

    @staticmethod
    def dump_yaml(yaml_dict: YamlDict) -> str:
        return yaml.dump(yaml_dict, Dumper=PyYamlYamlModel.IndentationDumper, sort_keys=False)

    @staticmethod
    def read_yaml(
        main_yaml: ResourceStream,
        enable_include: bool = True,
        base_dir: Optional[Path] = None,
        resources: Optional[Dict[str, TextIO]] = None,
    ) -> YamlDict:
        return PyYamlYamlModel._read_yaml_helper(
            yaml_file=main_yaml,
            loader=PyYamlYamlModel.SafeLineLoader,
            enable_include=enable_include,
            base_dir=base_dir,
            resources=resources,
        )

    # start of validation/parsing methods

    @property
    def facility_resource_names(self) -> List[str]:
        facility_input_data = self._internal_datamodel.get(EcalcYamlKeywords.facility_inputs, [])
        model_curves_data = [
            model.get(model_curves)
            for model in self._internal_datamodel.get(EcalcYamlKeywords.models, [])
            for model_curves in [EcalcYamlKeywords.consumer_chart_curves, EcalcYamlKeywords.consumer_chart_curve]
            if isinstance(model.get(model_curves), dict)
        ]
        resource_data = facility_input_data + model_curves_data
        resource_names = [
            data.get(EcalcYamlKeywords.file) for data in resource_data if data.get(EcalcYamlKeywords.file) is not None
        ]
        return resource_names

    @property
    def timeseries_resources(self) -> List[YamlTimeseriesResource]:
        timeseries_resources = []
        for resource in self._internal_datamodel.get(EcalcYamlKeywords.time_series, []):
            try:
                timeseries_type = YamlTimeseriesType[resource.get(EcalcYamlKeywords.type)]
            except KeyError as ke:
                raise DataValidationError(
                    data=resource,
                    message=f"Invalid timeseries, type should be one of {', '.join(YamlTimeseriesType)}. Got type '{resource.get(EcalcYamlKeywords.type)}'.",
                    dump_flow_style=DumpFlowStyle.BLOCK,
                    error_key=EcalcYamlKeywords.type,
                ) from ke
            timeseries_resources.append(
                YamlTimeseriesResource(
                    name=resource.get(EcalcYamlKeywords.file),
                    typ=timeseries_type,
                )
            )
        return timeseries_resources

    @property
    def all_resource_names(self) -> List[str]:
        facility_resource_names = self.facility_resource_names
        timeseries_resource_names = [resource.name for resource in self.timeseries_resources]
        return [*facility_resource_names, *timeseries_resource_names]

    @property
    def variables(self) -> YamlVariables:
        if not isinstance(self._internal_datamodel, dict):
            raise ValidationError("Yaml model is invalid.")

        variables = self._internal_datamodel.get(EcalcYamlKeywords.variables, {})
        try:
            return TypeAdapter(YamlVariables).validate_python(variables)
        except PydanticValidationError as e:
            raise DtoValidationError(data=variables, validation_error=e) from e

    @property
    def yaml_variables(self) -> Dict[YamlVariableReferenceId, dict]:
        if not isinstance(self._internal_datamodel, dict):
            return {}

        return self._internal_datamodel.get(EcalcYamlKeywords.variables, {})

    @property
    def facility_inputs(self):
        return self._internal_datamodel.get(EcalcYamlKeywords.facility_inputs, [])

    @property
    def time_series(self) -> List[YamlTimeSeriesCollection]:
        time_series = []
        for time_series_data in self._internal_datamodel.get(EcalcYamlKeywords.time_series, []):
            try:
                time_series.append(TypeAdapter(YamlTimeSeriesCollection).validate_python(time_series_data))
            except PydanticValidationError as e:
                raise DtoValidationError(data=time_series_data, validation_error=e) from e

        return time_series

    @property
    def models(self):
        return self._internal_datamodel.get(EcalcYamlKeywords.models, [])

    @property
    def fuel_types(self):
        return self._internal_datamodel.get(EcalcYamlKeywords.fuel_types, [])

    @property
    def installations(self):
        return self._internal_datamodel.get(EcalcYamlKeywords.installations, [])

    @property
    def start(self) -> Optional[datetime.datetime]:
        start_value = self._internal_datamodel.get(EcalcYamlKeywords.start)
        return convert_date_to_datetime(start_value) if start_value is not None else None

    @property
    def end(self) -> Optional[datetime.datetime]:
        end_value = self._internal_datamodel.get(EcalcYamlKeywords.end)
        return convert_date_to_datetime(end_value) if end_value is not None else None

    @property
    def dates(self):
        """All dates in the yaml."""
        return set(find_date_keys_in_yaml(self._internal_datamodel))

    def validate(self) -> Self:
        try:
            YamlAsset.model_validate(self._internal_datamodel)
            return self
        except PydanticValidationError as e:
            raise DtoValidationError(data=self._internal_datamodel, validation_error=e) from e


def find_date_keys_in_yaml(yaml_object: Union[List, Dict]) -> List[datetime.datetime]:
    """The function will add any dates found in the yaml_object to the list named output.

    :param yaml_object: The content (or subset) of a yaml file
    :type yaml_object: Union[List, Dict, CommentedMap]
    :return: The list with dates given as input to the function with any dates found in the yaml_object added to it
    :rtype: List[datetime.datetime]
    """

    def common_iterable(obj: Union[List, Dict]) -> Union[Dict, Iterator[int]]:
        """Helper function when iteration over something we beforehand don't know
        whether is a Dict, List or CommentedMap.

        :param obj: A subset of a nested YAML file to iterate over
        :type obj: Union[List, Dict]
        :return: The object if the object is a dict, or the indices of the list if the object is a list
        :rtype: Union[Dict, Iterator[int]]
        """
        if isinstance(obj, dict):
            return obj
        else:
            return (idx for idx, value in enumerate(obj))

    output = []
    for index in common_iterable(yaml_object):
        if isinstance(index, (datetime.date, datetime.datetime)):
            index_to_datetime = convert_date_to_datetime(index)
            if index_to_datetime not in output:
                output.append(index_to_datetime)
        if isinstance(yaml_object[index], (dict, list)):  # type: ignore
            output.extend(find_date_keys_in_yaml(yaml_object[index]))  # type: ignore

    return output
