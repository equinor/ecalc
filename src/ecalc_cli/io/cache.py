from dataclasses import dataclass, field
from pathlib import Path

from libecalc import dto
from libecalc.application.graph_result import EnergyCalculatorResult, GraphResult
from libecalc.common.run_info import RunInfo
from libecalc.dto.base import EcalcBaseModel
from libecalc.dto.result import EcalcModelResult

from ecalc_cli.logger import logger


class CacheData(EcalcBaseModel):
    """Data model for content in cache."""

    component_dto: dto.Asset
    results: EnergyCalculatorResult


@dataclass
class Cache:
    """Data class for CLI cache, storing model, results and run info."""

    user_specified_output_path: Path
    cache_path: Path = field(init=False)
    results_path: Path = field(init=False)
    run_info_path: Path = field(init=False)

    def __post_init__(self):
        self.cache_path = self.user_specified_output_path / ".ecalc"
        self.cache_path.mkdir(mode=0o770, exist_ok=True)
        self.results_path = self.cache_path / "results.json"
        self.run_info_path = self.cache_path / "run_info.json"

    def write_results(self, results: GraphResult, component_dto: dto.Asset):
        """Write results to cache.

        Args:
            results: Model results
            component_dto: Model used

        Returns:

        """
        logger.info(f"Writing results to cache '{self.cache_path}'.")
        self.results_path.touch(mode=0o660, exist_ok=True)
        cache_data = CacheData(
            results=results.get_results(),
            component_dto=component_dto,
        )
        self.results_path.write_text(cache_data.model_dump_json())

    def write_run_info(self, run_info: RunInfo):
        """Write meta information about the run to the cache.

        Args:
            run_info: A data model containing meta data of a eCalc run

        Returns:

        """
        logger.info(f"Writing run info to cache '{self.cache_path}'.")
        self.run_info_path.touch(mode=0o660, exist_ok=True)
        self.run_info_path.write_text(run_info.model_dump_json())

    def load_run_info(self) -> RunInfo:
        """Load metadata about run from cache.

        Returns:
            Cached metadata about a eCalc run

        Raises:
            ValueError: If the run info filepath is not set.

        """
        if not self.run_info_path.is_file():
            msg = "Could not find run info in this directory. Run the model again to generate results."
            logger.error(msg)
            raise ValueError(msg)

        return RunInfo.model_validate_json(self.run_info_path.read_text())

    def load_results(self) -> EcalcModelResult:
        """Load cached results from an ecalc run.

        Returns:
            Ecalc run results for a model

        Raises:
            ValueError: If the results path is not set

        """
        if not self.results_path.is_file():
            msg = "Could not find results in this directory, make sure you run 'ecalc show' from the output directory of 'ecalc run' (or specify --outputfolder). Run the model again if no output directory exists."
            raise ValueError(msg)
        cached_text = self.results_path.read_text()
        cache_data = CacheData.model_validate_json(cached_text)
        graph = cache_data.component_dto.get_graph()

        return GraphResult(
            graph=graph,
            emission_results=cache_data.results.emission_results,
            consumer_results=cache_data.results.consumer_results,
            variables_map=cache_data.results.variables_map,
        ).get_asset_result()
