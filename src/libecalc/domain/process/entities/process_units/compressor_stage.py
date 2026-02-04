import abc

from libecalc.domain.process.process_system.process_unit import ProcessUnit


class CompressorStage(ProcessUnit, abc.ABC):
    @abc.abstractmethod
    def get_minimum_rate(self) -> float:
        """

        Returns: the minimum rate for the current shaft speed

        """
        ...
