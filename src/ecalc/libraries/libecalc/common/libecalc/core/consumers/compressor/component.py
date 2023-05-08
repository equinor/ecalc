from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

import numpy as np
from libecalc.common.exceptions import ProgrammingError
from libecalc.common.temporal_model import TemporalModel
from libecalc.common.units import Unit
from libecalc.common.utils.rates import TimeSeriesBoolean, TimeSeriesRate
from libecalc.core.consumers.base import BaseConsumerWithoutOperationalSettings
from libecalc.core.models.compressor import CompressorModel, create_compressor_model
from libecalc.core.models.compressor.train.variable_speed_compressor_train_common_shaft_multiple_streams_and_pressures import (
    VariableSpeedCompressorTrainCommonShaftMultipleStreamsAndPressures,
)
from libecalc.core.models.results.compressor import CompressorTrainResult
from libecalc.core.result import EcalcModelResult
from libecalc.core.result.results import GenericComponentResult
from libecalc.dto.core_specs.compressor.operational_settings import (
    CompressorOperationalSettings,
)


class Compressor(BaseConsumerWithoutOperationalSettings):
    def __init__(self, id: str, energy_usage_model: Dict[datetime, CompressorModel]):
        self.id = id
        self._temporal_model = TemporalModel(
            data={timestep: create_compressor_model(model) for timestep, model in energy_usage_model.items()}
        )

        self._operational_settings: Optional[CompressorOperationalSettings] = None

    def get_max_rate(self, operational_settings: CompressorOperationalSettings) -> List[float]:
        results = []
        for period, compressor in self._temporal_model.items():
            operational_settings_this_period = operational_settings.get_subset_from_period(period)
            results.extend(
                compressor.get_max_standard_rate(
                    suction_pressures=np.asarray(operational_settings_this_period.inlet_pressure.values),
                    discharge_pressures=np.asarray(operational_settings_this_period.outlet_pressure.values),
                ).tolist()
            )
        return results

    @property
    def operational_settings(self) -> CompressorOperationalSettings:
        if self._operational_settings is None:
            raise ProgrammingError("Operational settings has not been set. Need to call evaluate first.")
        return self._operational_settings

    def evaluate(
        self,
        operational_settings: CompressorOperationalSettings,
    ) -> EcalcModelResult:
        """Todo:
        Implement Multiple Streams
        Handle regularity outside
        Take Lists as input. Then the model will convert to arrays.
        """
        self._operational_settings = operational_settings
        model_results = []
        evaluated_timesteps = []
        for period, compressor in self._temporal_model.items():
            operational_settings_this_period = operational_settings.get_subset_from_period(period)
            evaluated_timesteps.extend(operational_settings_this_period.timesteps)
            if isinstance(compressor, VariableSpeedCompressorTrainCommonShaftMultipleStreamsAndPressures):
                raise NotImplementedError("Need to implement this")
            elif issubclass(type(compressor), CompressorModel):
                model_result = compressor.evaluate_rate_ps_pd(
                    rate=np.sum([rate.values for rate in operational_settings_this_period.stream_day_rates], axis=0),
                    suction_pressure=np.asarray(operational_settings_this_period.inlet_pressure.values),
                    discharge_pressure=np.asarray(operational_settings_this_period.outlet_pressure.values),
                )
                model_results.append(model_result)

        aggregated_result: Optional[CompressorTrainResult] = None
        for model_result in model_results:
            if aggregated_result is None:
                aggregated_result = model_result
            else:
                aggregated_result.extend(model_result)

        component_result = GenericComponentResult(
            timesteps=evaluated_timesteps,
            power=TimeSeriesRate(
                values=aggregated_result.power, timesteps=evaluated_timesteps, unit=aggregated_result.power_unit
            ),
            energy_usage=TimeSeriesRate(
                values=aggregated_result.energy_usage,
                timesteps=evaluated_timesteps,
                unit=aggregated_result.energy_usage_unit,
            ),
            is_valid=TimeSeriesBoolean(
                values=aggregated_result.is_valid, timesteps=evaluated_timesteps, unit=Unit.NONE
            ),
            id=self.id,
        )

        return EcalcModelResult(
            component_result=component_result,
            sub_components=[],
            models=[],
        )
