import numpy as np
from numpy.typing import NDArray

from libecalc.domain.infrastructure.energy_components.legacy_consumer.system.consumer_function import SystemComponent
from libecalc.domain.process.compressor.core.base import CompressorModel, CompressorWithTurbineModel
from libecalc.domain.process.compressor.core.sampled import CompressorModelSampled
from libecalc.domain.process.compressor.core.train.base import CompressorTrainModel
from libecalc.domain.process.core.results import EnergyFunctionResult
from libecalc.domain.process.pump.pump import PumpModel
from libecalc.domain.process.value_objects.fluid_stream.fluid_factory import FluidFactoryInterface


class ConsumerSystemComponent(SystemComponent):
    def __init__(
        self,
        name: str,
        facility_model: PumpModel | CompressorModel | CompressorModelSampled,
        fluid_factory: FluidFactoryInterface | None = None,
    ):
        self._name = name
        self._facility_model = facility_model
        self._fluid_factory = fluid_factory

    @property
    def name(self) -> str:
        return self._name

    def get_max_standard_rate(
        self,
        suction_pressure: NDArray[np.float64],
        discharge_pressure: NDArray[np.float64],
        fluid_density: NDArray[np.float64] = None,
    ) -> NDArray[np.float64]:
        if isinstance(self._facility_model, CompressorTrainModel):
            return self._facility_model.get_max_standard_rate(
                suction_pressures=suction_pressure,
                discharge_pressures=discharge_pressure,
                fluid_factory=self._fluid_factory,
            )
        elif isinstance(self._facility_model, PumpModel):
            assert fluid_density is not None
            return self._facility_model.get_max_standard_rates(
                suction_pressures=suction_pressure,
                discharge_pressures=discharge_pressure,
                fluid_densities=fluid_density,
            )
        elif isinstance(self._facility_model, CompressorWithTurbineModel):
            if isinstance(self._facility_model.compressor_model, CompressorModelSampled):
                return self._facility_model.get_max_standard_rate(
                    suction_pressures=suction_pressure,
                    discharge_pressures=discharge_pressure,
                )
            else:
                return self._facility_model.get_max_standard_rate(
                    suction_pressures=suction_pressure,
                    discharge_pressures=discharge_pressure,
                    fluid_factory=self._fluid_factory,
                )
        else:
            assert isinstance(self._facility_model, CompressorModelSampled)
            return self._facility_model.get_max_standard_rate(
                suction_pressures=suction_pressure,
                discharge_pressures=discharge_pressure,
            )

    def evaluate(
        self,
        rate: NDArray[np.float64],
        suction_pressure: NDArray[np.float64],
        discharge_pressure: NDArray[np.float64],
        fluid_density: NDArray[np.float64] = None,
    ) -> EnergyFunctionResult:
        if isinstance(self._facility_model, PumpModel):
            assert fluid_density is not None
            return self._facility_model.evaluate_rate_ps_pd_density(
                rates=rate,
                suction_pressures=suction_pressure,
                discharge_pressures=discharge_pressure,
                fluid_densities=fluid_density,
            )
        elif isinstance(self._facility_model, CompressorTrainModel):
            consumer_model = self._facility_model
            assert self._fluid_factory is not None
            consumer_model.set_evaluation_input(
                rate=rate,
                suction_pressure=suction_pressure,
                discharge_pressure=discharge_pressure,
                fluid_factory=self._fluid_factory,
            )
            return consumer_model.evaluate()
        elif isinstance(self._facility_model, CompressorWithTurbineModel):
            consumer_model = self._facility_model
            if isinstance(consumer_model.compressor_model, CompressorModelSampled):
                consumer_model.compressor_model.set_evaluation_input(
                    rate=rate,
                    suction_pressure=suction_pressure,
                    discharge_pressure=discharge_pressure,
                )
            else:
                assert self._fluid_factory is not None
                consumer_model.compressor_model.set_evaluation_input(
                    rate=rate,
                    suction_pressure=suction_pressure,
                    discharge_pressure=discharge_pressure,
                    fluid_factory=self._fluid_factory,
                )
            return consumer_model.evaluate()
        else:
            consumer_model = self._facility_model
            assert isinstance(consumer_model, CompressorModelSampled)
            consumer_model.set_evaluation_input(
                rate=rate,
                suction_pressure=suction_pressure,
                discharge_pressure=discharge_pressure,
            )
            return consumer_model.evaluate()
