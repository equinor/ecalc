from typing import assert_never

import numpy as np
from numpy.typing import NDArray

from libecalc.domain.infrastructure.energy_components.legacy_consumer.system.consumer_function import SystemComponent
from libecalc.domain.process.compressor.core.base import CompressorModel, CompressorWithTurbineModel
from libecalc.domain.process.core.results import EnergyFunctionResult
from libecalc.domain.process.pump.pump import PumpModel
from libecalc.domain.process.value_objects.fluid_stream.fluid_factory import FluidFactoryInterface


class ConsumerSystemComponent(SystemComponent):
    def __init__(
        self,
        name: str,
        facility_model: PumpModel | CompressorModel,
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
        if isinstance(self._facility_model, CompressorModel):
            return self._facility_model.get_max_standard_rate(
                suction_pressures=suction_pressure,
                discharge_pressures=discharge_pressure,
            )
        elif isinstance(self._facility_model, PumpModel):
            assert fluid_density is not None
            return self._facility_model.get_max_standard_rates(
                suction_pressures=suction_pressure,
                discharge_pressures=discharge_pressure,
                fluid_densities=fluid_density,
            )

        assert_never(self._facility_model)

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
        else:
            assert isinstance(self._facility_model, CompressorModel)
            consumer_model = self._facility_model
            consumer_model.set_evaluation_input(
                rate=rate,
                suction_pressure=suction_pressure,
                discharge_pressure=discharge_pressure,
                fluid_factory=self._fluid_factory,
            )
            if isinstance(consumer_model, CompressorWithTurbineModel):
                consumer_model.compressor_model.check_for_undefined_stages()
            else:
                consumer_model.check_for_undefined_stages()

            return consumer_model.evaluate()
