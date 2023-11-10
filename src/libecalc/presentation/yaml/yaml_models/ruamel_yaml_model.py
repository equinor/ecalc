import io
from pathlib import Path
from typing import Any, Dict, Optional, TextIO

from ruamel.yaml import YAML

from libecalc.common.errors.exceptions import (
    EcalcError,
    EcalcErrorType,
    ProgrammingError,
)
from libecalc.presentation.yaml.yaml_entities import ResourceStream
from libecalc.presentation.yaml.yaml_models.yaml_model import YamlModel


class RuamelYamlModel(YamlModel):
    """Implementation of yaml model using Ruamel library
    Validation has currently not been implemented.
    """

    def __init__(self, internal_datamodel: Dict[str, Any], instantiated_through_read: bool = False):
        """To avoid mistakes, make sure that this is only instantiated through read method/named constructor
        :param instantiated_through_read: set to True to allow to use constructor.
        """
        if not instantiated_through_read:
            raise ProgrammingError(f"{self.__class__} can only be instantiated through read() method/named constructor")

        super().__init__(internal_datamodel=internal_datamodel)

    def dump(self) -> str:
        """Dumps the model to a string buffer and returns it
        :return:
        """
        if self._internal_datamodel is None:
            raise ProgrammingError("You cannot dump a model without first reading one. Use read() to read a model.")

        string_buffer: io.StringIO = io.StringIO()
        try:
            string_buffer.seek(0)
            self.__get_loader().dump(self._internal_datamodel, string_buffer)
            ret = string_buffer.getvalue()
        finally:
            string_buffer.close()

        return ret

    @staticmethod
    def __get_loader(
        enable_include: bool = False,
        base_dir: Optional[Path] = None,
        resources: Optional[Dict[str, TextIO]] = None,
    ) -> YAML:
        yaml_loader = YAML(typ="rt")  # rt is default, subclass of safe, so it is ok to use
        yaml_loader.preserve_quotes = True  # just keep the original quoting, preserved e.g. " or ' as it was
        # yaml_loader.explicit_start = True  # Require/set that yaml should start with ---
        yaml_loader.default_flow_style = (
            False  # do not serialize with nested mapping for collections, use block style. default. False in pyyaml
        )
        yaml_loader.indent(mapping=2, sequence=4, offset=2)  # nice formatting

        if enable_include:

            @yaml_loader.register_class
            class IncludeConstructor:
                yaml_tag = "!include"

                def __init__(self, string):
                    self._string = string

                @classmethod
                def from_yaml(cls, constructor, node):
                    if resources:
                        yaml_resource = ResourceStream(name=node.value, stream=resources[node.value])
                        return RuamelYamlModel._load(
                            yaml_file=yaml_resource,
                            base_dir=base_dir,
                            resources=resources,
                            enable_include=enable_include,
                        )
                    else:
                        return RuamelYamlModel._load(
                            yaml_file=ResourceStream(name=node.value, stream=Path(base_dir / node.value).open("r")),
                            base_dir=base_dir,
                            resources=resources,
                            enable_include=enable_include,
                        )

                def __repr__(self):
                    return repr(self._string)

        return yaml_loader

    @classmethod
    def read(
        cls,
        main_yaml: ResourceStream,
        base_dir: Optional[Path] = None,
        resources: Optional[Dict[str, TextIO]] = None,
        enable_include: bool = False,
    ) -> "RuamelYamlModel":
        """Class constructor.

        Chaining method

        Loads the yaml into memory for continiued work on it
        """
        internal_datamodel = RuamelYamlModel._load(
            yaml_file=main_yaml, resources=resources, enable_include=enable_include, base_dir=base_dir
        )
        self = cls(internal_datamodel=internal_datamodel, instantiated_through_read=True)
        return self

    @staticmethod
    def _load(
        yaml_file: ResourceStream,
        base_dir: Optional[Path] = None,
        resources: Optional[Dict[str, TextIO]] = None,
        enable_include: bool = False,
    ) -> Any:
        """Internal loading of yaml files, main and includes
        :param yaml_file:
        :return:
        """
        try:
            return RuamelYamlModel.__get_loader(
                resources=resources, enable_include=enable_include, base_dir=base_dir
            ).load(yaml_file)
        except KeyError as ke:
            raise EcalcError(
                title="Bad Yaml file", message=f"Error occurred while loading yaml file, key {ke} not found"
            ) from ke
        except Exception as e:
            raise EcalcError(
                error_type=EcalcErrorType.CLIENT_ERROR,
                title="Error loading yaml",
                message="We are not able to load the yaml due to an error: " + str(e),
            ) from e
