import io
from pathlib import Path
from typing import Dict, List

from libecalc.fixtures import YamlCase
from libecalc.infrastructure.file_io import read_resource_from_filepath
from libecalc.presentation.yaml.yaml_entities import Resource


def _read_main_file(main_file_path: Path) -> io.StringIO:
    with open(main_file_path) as f:
        lines = f.read()
        return io.StringIO(lines)


def _read_resources(directory: Path, resource_names: List[str]) -> Dict[str, Resource]:
    resources = {}
    for resource_name in resource_names:
        resources[resource_name] = read_resource_from_filepath(directory / resource_name)
    return resources


class YamlCaseLoader:
    @staticmethod
    def load(case_path: Path, main_file: str, resource_names: List[str]):
        case_data_path = case_path
        main_file_path = case_data_path / main_file
        return YamlCase(
            main_file_path=main_file_path,
            main_file=_read_main_file(main_file_path),
            resources=_read_resources(directory=main_file_path.parent, resource_names=resource_names),
        )
