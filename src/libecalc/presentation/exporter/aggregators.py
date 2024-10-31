import abc

from libecalc.common.logger import logger
from libecalc.common.time_utils import Frequency
from libecalc.presentation.exporter.appliers import Applier
from libecalc.presentation.exporter.domain.exportable import ExportableSet, ExportableType
from libecalc.presentation.exporter.dto.dtos import GroupedQueryResult, QueryResult


class Aggregator(abc.ABC):
    @abc.abstractmethod
    def aggregate(
        self,
        energy_calculator_result: ExportableSet,
    ) -> list[GroupedQueryResult]:
        """Each entry in this list will be handled separately
        Should ideally only work on one level in the hierarchy, more than one level
        at a time makes it inconsistent, so we should ideally provide which subtree
        to work on and aggregate, but since we do not have a tree nor graph...and specific
        components we do like this now...

        may be changed with more generic result, where we rely on a tree/graph, IDs and parent/children...

        TODO/NOTE: The aggregator may define at which level to aggregate, and we may have different
        aggregators for each export, that can be combined...
        :param model_dto:
        :param energy_calculator_result:
        :return:
        """
        pass


class InstallationAggregator(Aggregator):
    """this aggregator will initially serve as a "aggregate at installation level", before
    we hopefully make it possible to aggregate at any level, specified by user...

    - an entity in database for operators to change in web app
    - a config file...plug-in like for different exporters...ad-hoc, quick way;
    possibly users has a config-resource to define this, may be too complicated for
    many users though

    Now, quick way of just adding a lot of filters etc
    """

    def __init__(self, frequency: Frequency, appliers: list[Applier]):
        self.frequency = frequency
        self.appliers = appliers

    def aggregate(
        self,
        energy_calculator_result: ExportableSet,
    ) -> list[GroupedQueryResult]:
        """Aggregates data at installation level.

        TODO: Appliers should be serializable...or possible to convert to dict or dataframe
        in order to easily format...

        how to format to json, csv etc should be done by an external formatter....
        because we will easily get different requirements...

        Get a list of all the appliers that should be run
        on the resultset, in general the appliers should
        work like SQL; tell what to do, not how to do it,
        then we can easily replace implementation later of
        how we filter, ie. with new result set from ecalc
        calculator

        NOTE: str may be total, or name of installation
        :return:
        """
        aggregated_installation_results: list[GroupedQueryResult] = []
        for installation in energy_calculator_result.get_from_type(ExportableType.INSTALLATION):
            installation_name = installation.get_name()
            single_results: list[QueryResult] = []
            for applier in self.appliers:
                applier_result = applier.apply(installation, self.frequency)

                if applier_result:
                    single_results.append(applier_result)
                else:
                    logger.debug(f"No '{applier.name}' result for installation '{installation_name}'.")

            aggregated_installation_results.append(
                GroupedQueryResult(group_name=installation_name, query_results=single_results)
            )
        return aggregated_installation_results
