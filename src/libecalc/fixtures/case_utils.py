from pathlib import Path

from libecalc.fixtures import YamlCase
from libecalc.infrastructure.file_io import EcalcFile, _dataframe_to_resource, read_csv
from libecalc.presentation.yaml.yaml_entities import MemoryResource


def read_resource_from_filepath(resource_path: Path) -> MemoryResource:
    """Read resource from filepath without validation, should only be used as a util for tests/fixtures."""
    if EcalcFile.is_csv(resource_path):
        with open(resource_path) as resource_file:
            resource_df = read_csv(resource_file)
            return _dataframe_to_resource(resource_df)
    else:
        raise ValueError(f"Invalid file extension: {resource_path}")


def _read_resources(directory: Path, resource_names: list[str]) -> dict[str, MemoryResource]:
    resources = {}
    for resource_name in resource_names:
        resources[resource_name] = read_resource_from_filepath(directory / resource_name)
    return resources


class YamlCaseLoader:
    @staticmethod
    def load(case_path: Path, main_file: str, resource_names: list[str]):
        case_data_path = case_path
        main_file_path = case_data_path / main_file
        return YamlCase(
            main_file_path=main_file_path,
            resources=_read_resources(directory=main_file_path.parent, resource_names=resource_names),
        )
