from pathlib import Path

from libecalc.fixtures import YamlCase
from libecalc.presentation.yaml.yaml_entities import MemoryResource


def _read_resources(directory: Path, resource_names: list[str]) -> dict[str, MemoryResource]:
    return {name: MemoryResource.from_path(directory / name, allow_nans=True) for name in resource_names}


class YamlCaseLoader:
    @staticmethod
    def load(case_path: Path, main_file: str, resource_names: list[str]):
        case_data_path = case_path
        main_file_path = case_data_path / main_file
        return YamlCase(
            main_file_path=main_file_path,
            resources=_read_resources(directory=main_file_path.parent, resource_names=resource_names),
        )
