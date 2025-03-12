import datetime
import re
from collections.abc import Iterable, Iterator
from copy import deepcopy
from pathlib import Path
from typing import Any, Self, TextIO

import yaml
from pydantic import TypeAdapter
from pydantic import ValidationError as PydanticValidationError
from yaml import (
    SafeLoader,
)

from libecalc.common.errors.exceptions import ProgrammingError
from libecalc.common.time_utils import convert_date_to_datetime
from libecalc.dto.utils.validators import (
    COMPONENT_NAME_ALLOWED_CHARS,
    COMPONENT_NAME_PATTERN,
)
from libecalc.presentation.yaml.file_context import FileMark
from libecalc.presentation.yaml.validation_errors import (
    DataValidationError,
    DtoValidationError,
    DumpFlowStyle,
)
from libecalc.presentation.yaml.yaml_entities import (
    ResourceStream,
    YamlTimeseriesResource,
    YamlTimeseriesType,
)
from libecalc.presentation.yaml.yaml_keywords import EcalcYamlKeywords
from libecalc.presentation.yaml.yaml_models.exceptions import (
    DuplicateKeyError,
    FileContext,
    YamlError,
)
from libecalc.presentation.yaml.yaml_models.yaml_model import YamlConfiguration, YamlValidator
from libecalc.presentation.yaml.yaml_node import YamlDict, YamlList
from libecalc.presentation.yaml.yaml_types.components.yaml_asset import YamlAsset
from libecalc.presentation.yaml.yaml_types.components.yaml_installation import YamlInstallation
from libecalc.presentation.yaml.yaml_types.facility_model.yaml_facility_model import (
    YamlFacilityModel,
)
from libecalc.presentation.yaml.yaml_types.fuel_type.yaml_fuel_type import YamlFuelType
from libecalc.presentation.yaml.yaml_types.models import YamlConsumerModel
from libecalc.presentation.yaml.yaml_types.time_series.yaml_time_series import (
    YamlTimeSeriesCollection,
)
from libecalc.presentation.yaml.yaml_types.yaml_default_datetime import YamlDefaultDatetime
from libecalc.presentation.yaml.yaml_types.yaml_variable import (
    YamlVariable,
    YamlVariableReferenceId,
    YamlVariables,
)
from libecalc.presentation.yaml.yaml_validation_context import (
    YamlModelValidationContext,
)


class PyYamlYamlModel(YamlValidator, YamlConfiguration):
    """Implementation of yaml model using PyYaml library
    Keeping comments and horizontal lists on loading currently not supported!
    """

    @classmethod
    def get_validator(cls, *args, **kwargs) -> "YamlValidator":
        return cls.read(*args, **kwargs)

    def __init__(self, internal_datamodel: dict[str, Any], name: str, instantiated_through_read: bool = False):
        """To avoid mistakes, make sure that this is only instantiated through read method/named constructor
        :param instantiated_through_read: set to True to allow to use constructor.
        """
        if not instantiated_through_read:
            raise ProgrammingError(f"{self.__class__} can only be instantiated through read() method/named constructor")

        super().__init__(internal_datamodel=internal_datamodel, name=name)

    def dump(self) -> str:
        if self._internal_datamodel is None:
            raise ProgrammingError("You cannot dump a model without first reading one. Use read() to read a model.")

        return PyYamlYamlModel.dump_yaml(self._internal_datamodel)

    @classmethod
    def read(
        cls,
        main_yaml: ResourceStream,
        base_dir: Path | None = None,
        resources: dict[str, TextIO] | None = None,
        enable_include: bool = True,
    ) -> "PyYamlYamlModel":
        internal_datamodel = PyYamlYamlModel.read_yaml(
            main_yaml=main_yaml, resources=resources, base_dir=base_dir, enable_include=enable_include
        )
        self = cls(internal_datamodel=internal_datamodel, name=main_yaml.name, instantiated_through_read=True)
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

        def __init__(self, base_dir: Path | None = None, resources: dict[str, TextIO] | None = None):
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
            return super().increase_indent(flow, False)

    class YamlReader:
        def __init__(
            self,
            loader: type[yaml.SafeLoader],
            enable_include: bool = True,
            base_dir: Path | None = None,
            resources: dict[str, TextIO] | None = None,
        ):
            self.__loader = loader
            if enable_include and (base_dir or resources):
                loader.add_constructor(
                    "!include",
                    PyYamlYamlModel.IncludeConstructor(base_dir=base_dir, resources=resources),
                )

        def load(self, yaml_file: ResourceStream):
            class UniqueKeyLoader(self.__loader):  # type: ignore[name-defined]
                def construct_mapping(self, node, deep=False):
                    mapping = set()
                    for key_node, _ in node.value:
                        each_key = self.construct_object(key_node, deep=deep)
                        if each_key in mapping:
                            raise DuplicateKeyError(
                                key=each_key,
                                file_context=FileContext(
                                    name=key_node.start_mark.name,
                                    start=FileMark(
                                        line_number=key_node.start_mark.line + 1,
                                        column_number=key_node.start_mark.column + 1,
                                    ),
                                ),
                            )
                        mapping.add(each_key)
                    return super().construct_mapping(node, deep)

            if re.search(COMPONENT_NAME_PATTERN, Path(yaml_file.name).stem) is None:
                raise YamlError(
                    problem=f"The model file, {yaml_file.name}, contains illegal special characters. "
                    f"Allowed characters are {COMPONENT_NAME_ALLOWED_CHARS}",
                )
            try:
                return yaml.load(yaml_file, Loader=UniqueKeyLoader)  # noqa: S506 - loader should be SafeLoader
            except KeyError as e:
                raise YamlError(problem=f"Error occurred while loading yaml file, key {e} not found") from e

        def dump_and_load(self, yaml_file: ResourceStream):
            return yaml.dump(self.load(yaml_file), Dumper=PyYamlYamlModel.IndentationDumper, sort_keys=False)

    @staticmethod
    def _read_yaml_helper(
        yaml_file: ResourceStream,
        loader: type[yaml.SafeLoader],
        enable_include: bool = True,
        base_dir: Path | None = None,
        resources: dict[str, TextIO] | None = None,
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
        base_dir: Path | None = None,
        resources: dict[str, TextIO] | None = None,
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
        base_dir: Path | None = None,
        resources: dict[str, TextIO] | None = None,
    ) -> YamlDict:
        try:
            read_yaml = PyYamlYamlModel._read_yaml_helper(
                yaml_file=main_yaml,
                loader=PyYamlYamlModel.SafeLineLoader,
                enable_include=enable_include,
                base_dir=base_dir,
                resources=resources,
            )
            if read_yaml is None:
                raise yaml.YAMLError("YAML is empty")
            if not isinstance(read_yaml, dict):
                raise yaml.YAMLError("Not a valid YAML object")
            return read_yaml
        except yaml.YAMLError as e:
            file_context = None
            if hasattr(e, "problem_mark"):
                mark = e.problem_mark
                if mark is not None:
                    file_context = FileContext(
                        name=mark.name,
                        start=FileMark(
                            line_number=mark.line + 1,
                            column_number=mark.column + 1,
                        ),
                    )

            problem = "Invalid YAML file"
            if hasattr(e, "problem"):
                optional_problem = e.problem
                if optional_problem is not None:
                    problem = optional_problem

            raise YamlError(
                problem=problem,
                file_context=file_context,
            ) from e

    # start of validation/parsing methods
    @property
    def name(self):
        return self._name

    def _get_yaml_data_or_default(self, keyword, factory):
        """
        Function used to get data when we don't want validation to fail, only get the data if available.

        Args:
            keyword: keyword to get from the yaml
            factory: builtin type that should work as a factory and for typechecking

        Returns: data for keyword if available, else default created by factory

        """
        default = factory()
        if not isinstance(self._internal_datamodel, dict):
            return default

        data = self._internal_datamodel.get(keyword, default)

        if data is None or not isinstance(data, factory):
            return default

        return data

    def _get_yaml_list_or_empty(self, keyword: str) -> list:
        return self._get_yaml_data_or_default(keyword, list)

    def _get_yaml_dict_or_empty(self, keyword: str) -> dict:
        return self._get_yaml_data_or_default(keyword, dict)

    @property
    def facility_resource_names(self) -> list[str]:
        facility_input_data = self._get_yaml_list_or_empty(EcalcYamlKeywords.facility_inputs)
        model_curves_data = [
            model.get(model_curves)
            for model in self._get_yaml_list_or_empty(EcalcYamlKeywords.models)
            for model_curves in [EcalcYamlKeywords.consumer_chart_curves, EcalcYamlKeywords.consumer_chart_curve]
            if isinstance(model.get(model_curves), dict)
        ]
        resource_data = facility_input_data + model_curves_data
        resource_names = [
            data.get(EcalcYamlKeywords.file) for data in resource_data if data.get(EcalcYamlKeywords.file) is not None
        ]
        return resource_names

    @property
    def timeseries_resources(self) -> list[YamlTimeseriesResource]:
        timeseries_resources = []
        for resource in self._get_yaml_list_or_empty(EcalcYamlKeywords.time_series):
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
    def variables(self) -> YamlVariables:
        """
        Get variables, invalid variable definitions will be skipped.

        Returns: valid variables

        """
        variables = self._get_yaml_dict_or_empty(EcalcYamlKeywords.variables)

        valid_variables = {}
        for reference, variable in variables.items():
            try:
                reference = TypeAdapter(YamlVariableReferenceId).validate_python(reference)
                variable = TypeAdapter(YamlVariable).validate_python(variable)
                valid_variables[reference] = variable
            except PydanticValidationError:
                continue

        return valid_variables

    @property
    def yaml_variables(self) -> dict[YamlVariableReferenceId, dict]:
        """
        Get the internal data for variables directly.
        Returns:

        """
        return self._get_yaml_dict_or_empty(EcalcYamlKeywords.variables)

    @property
    def facility_inputs(self) -> list[YamlFacilityModel]:
        facility_inputs = []
        for facility_input in self._get_yaml_list_or_empty(EcalcYamlKeywords.facility_inputs):
            try:
                facility_inputs.append(TypeAdapter(YamlFacilityModel).validate_python(facility_input))
            except PydanticValidationError:
                pass

        return facility_inputs

    @property
    def models(self) -> list[YamlConsumerModel]:
        models = []
        for model in self._get_yaml_list_or_empty(EcalcYamlKeywords.models):
            try:
                models.append(TypeAdapter(YamlConsumerModel).validate_python(model))
            except PydanticValidationError:
                pass

        return models

    @property
    def time_series(self) -> list[YamlTimeSeriesCollection]:
        """
        Get only valid time series, i.e. don't fail if one is invalid.
        """
        time_series = []
        for time_series_data in self._get_yaml_list_or_empty(EcalcYamlKeywords.time_series):
            try:
                time_series.append(TypeAdapter(YamlTimeSeriesCollection).validate_python(time_series_data))
            except PydanticValidationError:
                pass

        return time_series

    @property
    def fuel_types(self):
        fuel_types = []
        for fuel_type in self._get_yaml_list_or_empty(EcalcYamlKeywords.fuel_types):
            try:
                fuel_types.append(TypeAdapter(YamlFuelType).validate_python(fuel_type))
            except PydanticValidationError:
                pass
        return fuel_types

    @property
    def installations(self) -> Iterable[YamlInstallation]:
        installations = []
        for installation in self._get_yaml_list_or_empty(EcalcYamlKeywords.installations):
            try:
                installations.append(TypeAdapter(YamlInstallation).validate_python(installation))
            except PydanticValidationError:
                pass
        return installations

    @property
    def start(self) -> datetime.datetime | None:
        start_value = self._internal_datamodel.get(EcalcYamlKeywords.start)
        return TypeAdapter(YamlDefaultDatetime).validate_python(start_value) if start_value is not None else None

    @property
    def end(self) -> datetime.datetime | None:
        end_value = self._internal_datamodel.get(EcalcYamlKeywords.end)
        return TypeAdapter(YamlDefaultDatetime).validate_python(end_value) if end_value is not None else None

    @property
    def dates(self):
        """All dates in the yaml."""
        return set(find_date_keys_in_yaml(self._internal_datamodel))

    def validate(self, context: YamlModelValidationContext) -> Self:
        try:
            YamlAsset.model_validate(deepcopy(self._internal_datamodel), context=context)
            return self
        except PydanticValidationError as e:
            raise DtoValidationError(data=self._internal_datamodel, validation_error=e) from e


def find_date_keys_in_yaml(yaml_object: list | dict) -> list[datetime.datetime]:
    """The function will add any dates found in the yaml_object to the list named output.

    :param yaml_object: The content (or subset) of a yaml file
    :type yaml_object: Union[List,dict, CommentedMap]
    :return: The list with dates given as input to the function with any dates found in the yaml_object added to it
    :rtype:list[datetime.datetime]
    """

    def common_iterable(obj: list | dict) -> dict | Iterator[int]:
        """Helper function when iteration over something we beforehand don't know
        whether is adict,list or CommentedMap.

        :param obj: A subset of a nested YAML file to iterate over
        :type obj: Union[List,dict]
        :return: The object if the object is a dict, or the indices of the list if the object is a list
        :rtype: Union[Dict, Iterator[int]]
        """
        if isinstance(obj, dict):
            return obj
        else:
            return (idx for idx, value in enumerate(obj))

    output = []
    for index in common_iterable(yaml_object):
        if isinstance(index, datetime.date | datetime.datetime):
            index_to_datetime = convert_date_to_datetime(index)
            if index_to_datetime not in output:
                output.append(index_to_datetime)
        if isinstance(yaml_object[index], dict | list):  # type: ignore
            output.extend(find_date_keys_in_yaml(yaml_object[index]))  # type: ignore

    return output
