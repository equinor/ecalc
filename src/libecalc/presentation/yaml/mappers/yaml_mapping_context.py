from libecalc.presentation.yaml.mappers.yaml_path import YamlPath
from libecalc.presentation.yaml.validation_errors import Location


class MappingContext:
    def __init__(self):
        self._name_map = {}

    def register_component_name(self, yaml_path: YamlPath, name: str):
        self._name_map[yaml_path.keys] = name

    def get_component_name(self, yaml_path: YamlPath) -> str | None:
        return self._name_map.get(yaml_path.keys)

    def get_location_from_yaml_path(self, yaml_path: YamlPath) -> Location:
        """
        Replace indices with names of the objects to create a Location, which is displayed to user
        """
        location_keys = []

        current_path = YamlPath()
        for key in yaml_path.keys:
            current_path = current_path.append(key)
            if isinstance(key, int):
                location_keys.append(self.get_component_name(current_path) or key)
            else:
                location_keys.append(key)

        return Location(keys=location_keys)
