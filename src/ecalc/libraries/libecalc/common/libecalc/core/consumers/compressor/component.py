from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

import numpy as np
from libecalc import dto
from libecalc.common.exceptions import ProgrammingError
from libecalc.common.temporal_model import TemporalModel
from libecalc.common.units import Unit
from libecalc.common.utils.rates import (
    TimeSeriesBoolean,
    TimeSeriesFloat,
    TimeSeriesRate,
)
from libecalc.core.consumers.base import BaseConsumerWithoutOperationalSettings
from libecalc.core.models.compressor import CompressorModel, create_compressor_model
from libecalc.core.models.compressor.train.variable_speed_compressor_train_common_shaft_multiple_streams_and_pressures import (
    VariableSpeedCompressorTrainCommonShaftMultipleStreamsAndPressures,
)
from libecalc.core.models.results.compressor import CompressorTrainResult
from libecalc.core.result import EcalcModelResult
from libecalc.core.result import results as core_results
from libecalc.dto.core_specs.compressor.operational_settings import (
    CompressorOperationalSettings,
)


class Compressor(BaseConsumerWithoutOperationalSettings):
    def __init__(self, id: str, energy_usage_model: Dict[datetime, dto.CompressorModel]):
        self.id = id
        self._temporal_model = TemporalModel(
            data={timestep: create_compressor_model(model) for timestep, model in energy_usage_model.items()}
        )

        self._operational_settings: Optional[CompressorOperationalSettings] = None

    def get_max_rate(self, operational_settings: CompressorOperationalSettings) -> List[float]:
        """
        For each timestep, get the maximum rate that this compressor can handle, given
        the operational settings given, such as in -and outlet pressures (current conditions)
        :param operational_settings:
        :return:
        """
        results = []
        for timestep in operational_settings.timesteps:
            compressor = self._temporal_model.get_model(timestep)
            operational_settings_this_timestep = operational_settings.get_subset_for_timestep(timestep)
            results.extend(
                compressor.get_max_standard_rate(
                    suction_pressures=np.asarray(operational_settings_this_timestep.inlet_pressure.values),
                    discharge_pressures=np.asarray(operational_settings_this_timestep.outlet_pressure.values),
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
        """
        Todo:
            Implement Multiple Streams
            Handle regularity outside
        """
        self._operational_settings = operational_settings

        model_results = []
        evaluated_timesteps = []

        # TODO: This is a false assumption and will be dealt with shortly (that the regularity is the same
        # for all timesteps, and only taken for the first timestep)
        evaluated_regularity = operational_settings.stream_day_rates[0].regularity
        for timestep in operational_settings.timesteps:
            compressor = self._temporal_model.get_model(timestep)
            operational_settings_for_timestep = operational_settings.get_subset_for_timestep(timestep)
            evaluated_timesteps.extend(operational_settings_for_timestep.timesteps)
            if isinstance(compressor, VariableSpeedCompressorTrainCommonShaftMultipleStreamsAndPressures):
                raise NotImplementedError("Need to implement this")
            elif issubclass(type(compressor), CompressorModel):
                model_result = compressor.evaluate_rate_ps_pd(
                    rate=np.sum([rate.values for rate in operational_settings_for_timestep.stream_day_rates], axis=0),
                    suction_pressure=np.asarray(operational_settings_for_timestep.inlet_pressure.values),
                    discharge_pressure=np.asarray(operational_settings_for_timestep.outlet_pressure.values),
                )
                model_results.append(model_result)

        aggregated_result: Optional[CompressorTrainResult] = None
        for model_result in model_results:
            if aggregated_result is None:
                aggregated_result = model_result
            else:
                aggregated_result.extend(model_result)

        energy_usage = TimeSeriesRate(
            values=aggregated_result.energy_usage,
            timesteps=evaluated_timesteps,
            unit=aggregated_result.energy_usage_unit,
            regularity=evaluated_regularity,
        )

        if energy_usage.unit == Unit.STANDARD_CUBIC_METER_PER_DAY:
            energy_usage = energy_usage.to_calendar_day()  # provide fuel usage in calendar day, same as legacy consumer

        component_result = core_results.CompressorResult(
            timesteps=evaluated_timesteps,
            power=TimeSeriesRate(
                values=aggregated_result.power,
                timesteps=evaluated_timesteps,
                unit=aggregated_result.power_unit,
                regularity=evaluated_regularity,
            ).fill_nan(0.0),
            energy_usage=energy_usage.fill_nan(0.0),
            is_valid=TimeSeriesBoolean(
                values=aggregated_result.is_valid, timesteps=evaluated_timesteps, unit=Unit.NONE
            ),
            id=self.id,
            recirculation_loss=TimeSeriesRate(
                values=aggregated_result.recirculation_loss,
                timesteps=evaluated_timesteps,
                unit=Unit.MEGA_WATT,
                regularity=evaluated_regularity,
            ),
            rate_exceeds_maximum=TimeSeriesBoolean(
                values=aggregated_result.rate_exceeds_maximum,
                timesteps=evaluated_timesteps,
                unit=Unit.NONE,
            ),
            outlet_pressure_before_choking=TimeSeriesFloat(
                values=aggregated_result.outlet_pressure_before_choking
                if aggregated_result.outlet_pressure_before_choking
                else [np.nan for _ in evaluated_timesteps],
                timesteps=evaluated_timesteps,
                unit=Unit.BARA,
            ),
        )

        return EcalcModelResult(
            component_result=component_result,
            sub_components=[],
            models=[
                core_results.CompressorModelResult(
                    name="N/A",  # No context available to populate model name
                    timesteps=evaluated_timesteps,
                    is_valid=TimeSeriesBoolean(
                        timesteps=evaluated_timesteps,
                        values=aggregated_result.is_valid,
                        unit=Unit.NONE,
                    ),
                    power=TimeSeriesRate(
                        timesteps=evaluated_timesteps,
                        values=aggregated_result.power,
                        unit=aggregated_result.power_unit,
                        regularity=evaluated_regularity,
                    )
                    if aggregated_result.power is not None
                    else None,
                    energy_usage=TimeSeriesRate(
                        timesteps=evaluated_timesteps,
                        values=aggregated_result.energy_usage,
                        unit=aggregated_result.energy_usage_unit,
                        regularity=evaluated_regularity,
                    ),
                    energy_usage_unit=aggregated_result.energy_usage_unit,
                    rate_sm3_day=aggregated_result.rate_sm3_day,
                    stage_results=aggregated_result.stage_results,
                    failure_status=aggregated_result.failure_status,
                )
            ],
        )
