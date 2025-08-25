from libecalc.common.logger import logger
from libecalc.domain.process.compressor.core.train.base import CompressorTrainModel
from libecalc.domain.process.compressor.dto import VariableSpeedCompressorTrain
from libecalc.domain.process.core.results.compressor import TargetPressureStatus
from libecalc.domain.process.value_objects.fluid_stream.fluid_factory import FluidFactoryInterface


class VariableSpeedCompressorTrainCommonShaft(CompressorTrainModel):
    """A model of a compressor train with variable speed

    In general, a compressor train (series of compressors) is running on a single shaft, meaning each stage will always
    have the same speed. Given inlet fluid conditions (composition, temperature, pressure, rate) and a shaft speed, the
    intermediate pressures (and temperature before cooling) between stages and the outlet pressure (and temperature) is
    given. To solve this for a given outlet pressure, one must iterate to find the speed.

    Compressor charts:
    The compressor charts must be pre-defined and have variable speed. Each compressor chart may either be
    1. Using a generic chart by specifying a design point
    2. Fully specified compressor chart

    FluidStream:
    Model of the fluid. See FluidStream
    For each stage, one must specify a compressor chart, an inlet temperature and whether to take out liquids after
    compression and cooling. In addition, one must specify the pressure drop from previous stage (It may be 0).
    The compressor train may be evaluated by one inlet through the entire train (fluid spec and rate), or by specifying
    one fluid stream per stage (to support incoming or outgoing streams between stages).

    """

    def __init__(
        self,
        data_transfer_object: VariableSpeedCompressorTrain,
        fluid_factory: FluidFactoryInterface,
    ):
        logger.debug(
            f"Creating VariableSpeedCompressorTrainCommonShaft with n_stages: {len(data_transfer_object.stages)}"
        )
        super().__init__(data_transfer_object, fluid_factory)
        self.data_transfer_object = data_transfer_object
