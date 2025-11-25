from typing import assert_never

import numpy as np
from numpy.typing import NDArray

from libecalc.domain.infrastructure.energy_components.legacy_consumer.system.consumer_function import SystemComponent
from libecalc.domain.process.compressor.core.base import CompressorWithTurbineModel
from libecalc.domain.process.compressor.core.sampled import CompressorModelSampled
from libecalc.domain.process.compressor.core.train.base import CompressorTrainModel
from libecalc.domain.process.core.results import EnergyFunctionResult
from libecalc.domain.process.pump.pump import PumpModel
from libecalc.domain.process.value_objects.fluid_stream.fluid_factory import FluidFactoryInterface


class ConsumerSystemComponent(SystemComponent):
    def __init__(
        self,
        name: str,
        facility_model: PumpModel | CompressorTrainModel | CompressorWithTurbineModel | CompressorModelSampled,
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
        model = self._facility_model
        if isinstance(model, CompressorTrainModel):
            return model.get_max_standard_rate(
                suction_pressures=suction_pressure,
                discharge_pressures=discharge_pressure,
                fluid_factory=self._fluid_factory,
            )
        elif isinstance(model, PumpModel):
            assert fluid_density is not None
            return model.get_max_standard_rates(
                suction_pressures=suction_pressure,
                discharge_pressures=discharge_pressure,
                fluid_densities=fluid_density,
            )
        elif isinstance(model, CompressorWithTurbineModel):
            if isinstance(model.compressor_model, CompressorModelSampled):
                return model.get_max_standard_rate(
                    suction_pressures=suction_pressure,
                    discharge_pressures=discharge_pressure,
                )
            return model.get_max_standard_rate(
                suction_pressures=suction_pressure,
                discharge_pressures=discharge_pressure,
                fluid_factory=self._fluid_factory,
            )
        elif isinstance(model, CompressorModelSampled):
            return model.get_max_standard_rate(
                suction_pressures=suction_pressure,
                discharge_pressures=discharge_pressure,
            )
        else:
            assert_never(model)

    def evaluate(
        self,
        rate: NDArray[np.float64],
        suction_pressure: NDArray[np.float64],
        discharge_pressure: NDArray[np.float64],
        fluid_density: NDArray[np.float64] = None,
    ) -> EnergyFunctionResult:
        model = self._facility_model
        if isinstance(model, PumpModel):
            assert fluid_density is not None
            return model.evaluate_rate_ps_pd_density(
                rates=rate,
                suction_pressures=suction_pressure,
                discharge_pressures=discharge_pressure,
                fluid_densities=fluid_density,
            )
        elif isinstance(model, CompressorTrainModel):
            assert self._fluid_factory is not None
            model.set_evaluation_input(
                rate=rate,
                suction_pressure=suction_pressure,
                discharge_pressure=discharge_pressure,
                fluid_factory=self._fluid_factory,
            )
            return model.evaluate()
        elif isinstance(model, CompressorWithTurbineModel):
            if isinstance(model.compressor_model, CompressorModelSampled):
                model.compressor_model.set_evaluation_input(
                    rate=rate,
                    suction_pressure=suction_pressure,
                    discharge_pressure=discharge_pressure,
                )
            else:
                assert self._fluid_factory is not None
                model.compressor_model.set_evaluation_input(
                    rate=rate,
                    suction_pressure=suction_pressure,
                    discharge_pressure=discharge_pressure,
                    fluid_factory=self._fluid_factory,
                )
            return model.evaluate()
        elif isinstance(model, CompressorModelSampled):
            model.set_evaluation_input(
                rate=rate,
                suction_pressure=suction_pressure,
                discharge_pressure=discharge_pressure,
            )
            return model.evaluate()

        else:
            assert_never(model)
