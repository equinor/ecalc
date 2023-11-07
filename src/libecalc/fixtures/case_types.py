from dataclasses import dataclass
from pathlib import Path
from typing import Dict, NamedTuple, TextIO

from libecalc import dto
from libecalc.presentation.yaml.yaml_entities import Resource


@dataclass
class YamlCase:
    resources: Dict[str, Resource]
    main_file: TextIO
    main_file_path: Path


class DTOCase(NamedTuple):
    ecalc_model: dto.Asset
    variables: dto.VariablesMap
