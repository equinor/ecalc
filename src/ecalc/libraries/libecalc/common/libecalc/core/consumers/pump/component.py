from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

import numpy as np
from libecalc import dto
from libecalc.common.temporal_model import TemporalModel
from libecalc.common.units import Unit
from libecalc.common.utils.rates import (
    TimeSeriesBoolean,
    TimeSeriesFloat,
    TimeSeriesRate,
)
from libecalc.core.consumers.base import BaseConsumerWithoutOperationalSettings
from libecalc.core.models.pump import create_pump_model
from libecalc.core.models.results import PumpModelResult
from libecalc.core.result import EcalcModelResult
from libecalc.core.result import results as core_results
from libecalc.dto.core_specs.pump.operational_settings import PumpOperationalSettings


class Pump(BaseConsumerWithoutOperationalSettings):
    def __init__(self, id: str, energy_usage_model: Dict[datetime, dto.PumpModel]):
        self.id = id
        self._temporal_model = TemporalModel(
            data={timestep: create_pump_model(model) for timestep, model in energy_usage_model.items()}
        )

        self._operational_settings = None

    def get_max_rate(self, operational_settings: PumpOperationalSettings) -> List[float]:
        """
        For each timestep, get the maximum rate that this pump can handle, given
        the operational settings given, such as in -and outlet pressures and fluid density (current conditions)
        :param operational_settings:
        :return:
        """
        results = []
        for timestep in operational_settings.timesteps:
            pump = self._temporal_model.get_model(timestep)
            operational_settings_this_timestep = operational_settings.get_subset_for_timestep(timestep)
            results.extend(
                pump.get_max_standard_rate(
                    suction_pressures=np.asarray(operational_settings_this_timestep.inlet_pressure.values),
                    discharge_pressures=np.asarray(operational_settings_this_timestep.outlet_pressure.values),
                    fluid_density=np.asarray(operational_settings_this_timestep.fluid_density.values),
                ).tolist()
            )
        return results

    @property
    def operational_settings(self) -> PumpOperationalSettings:
        return self._operational_settings

    def evaluate(
        self,
        operational_settings: PumpOperationalSettings,
    ) -> EcalcModelResult:
        """
        Todo:
            Handle regularity outside
        """
        self._operational_settings = operational_settings

        # Regularity is the same for all rate vectors.
        # In case of cross-overs or multiple streams, there may be multiple rate vectors.
        # TODO: False assumption, to be handled shortly
        regularity = operational_settings.stream_day_rates[0].regularity

        model_results = []
        evaluated_timesteps = []
        for timestep in operational_settings.timesteps:
            pump = self._temporal_model.get_model(timestep)
            operational_settings_for_timestep = operational_settings.get_subset_for_timestep(timestep)
            evaluated_timesteps.extend(operational_settings_for_timestep.timesteps)
            model_result = pump.evaluate_rate_ps_pd_density(
                rate=np.sum([rate.values for rate in operational_settings_for_timestep.stream_day_rates], axis=0),
                suction_pressures=np.asarray(operational_settings_for_timestep.inlet_pressure.values),
                discharge_pressures=np.asarray(operational_settings_for_timestep.outlet_pressure.values),
                fluid_density=np.asarray(operational_settings_for_timestep.fluid_density.values),
            )
            model_results.append(model_result)

        aggregated_result: Optional[PumpModelResult] = None
        for model_result in model_results:
            if aggregated_result is None:
                aggregated_result = model_result
            else:
                aggregated_result.extend(model_result)
        component_result = core_results.PumpResult(
            timesteps=evaluated_timesteps,
            power=TimeSeriesRate(
                values=aggregated_result.power,
                timesteps=evaluated_timesteps,
                unit=aggregated_result.power_unit,
                regularity=regularity,
            ).fill_nan(0.0),
            energy_usage=TimeSeriesRate(
                values=aggregated_result.energy_usage,
                timesteps=evaluated_timesteps,
                unit=aggregated_result.energy_usage_unit,
                regularity=regularity,
            ).fill_nan(0.0),
            inlet_liquid_rate_m3_per_day=TimeSeriesRate(
                values=aggregated_result.rate,
                timesteps=evaluated_timesteps,
                unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                regularity=regularity,
            ),
            inlet_pressure_bar=TimeSeriesFloat(
                values=aggregated_result.suction_pressure,
                timesteps=evaluated_timesteps,
                unit=Unit.BARA,
            ),
            outlet_pressure_bar=TimeSeriesFloat(
                values=aggregated_result.discharge_pressure,
                timesteps=evaluated_timesteps,
                unit=Unit.BARA,
            ),
            operational_head=TimeSeriesFloat(
                values=aggregated_result.operational_head,
                timesteps=evaluated_timesteps,
                unit=Unit.POLYTROPIC_HEAD_KILO_JOULE_PER_KG,
            ),
            is_valid=TimeSeriesBoolean(
                values=aggregated_result.is_valid, timesteps=evaluated_timesteps, unit=Unit.NONE
            ),
            id=self.id,
        )

        return EcalcModelResult(
            component_result=component_result,
            sub_components=[],
            models=[
                core_results.PumpModelResult(
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
                        regularity=regularity,
                    )
                    if aggregated_result.power is not None
                    else None,
                    energy_usage=TimeSeriesRate(
                        timesteps=evaluated_timesteps,
                        values=aggregated_result.energy_usage,
                        unit=aggregated_result.energy_usage_unit,
                        regularity=regularity,
                    ),
                    inlet_liquid_rate_m3_per_day=aggregated_result.rate,
                    inlet_pressure_bar=aggregated_result.suction_pressure,
                    outlet_pressure_bar=aggregated_result.discharge_pressure,
                    operational_head=aggregated_result.operational_head,
                )
            ],
        )
