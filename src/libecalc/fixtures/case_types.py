import io
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, NamedTuple, TextIO

from libecalc.common.variables import VariablesMap
from libecalc.dto import Asset
from libecalc.presentation.yaml.yaml_entities import MemoryResource


@dataclass
class YamlCase:
    resources: Dict[str, MemoryResource]
    main_file_path: Path

    @property
    def main_file(self) -> TextIO:
        with open(self.main_file_path) as f:
            lines = f.read()
            return io.StringIO(lines)


class DTOCase(NamedTuple):
    ecalc_model: Asset
    variables: VariablesMap
