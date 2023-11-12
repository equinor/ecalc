from datetime import datetime
from enum import Enum
from typing import Any, Dict, List

from libecalc.dto.base import ComponentType
from libecalc.dto.types import EnergyModelType
from libecalc.expression import Expression
from libecalc.presentation.yaml.model import YamlModel


class ItemsToEvaluate(str, Enum):
    # calculate_max_rate = "calculate_max_rate"
    # energy_usage_adjustment_constant = "energy_usage_adjustment_constant"
    # energy_adjustment_factor = "energy_adjustment_factor"
    # maximum_power = "maximum_power"
    pressure_drop_before_stage = "pressure_drop_before_stage"


class EvaluateModels:
    def __init__(
        self,
        model: YamlModel,
    ):
        self._variables_map = model.variables
        self._installations = model.dto.installations
        self._model = model

    def ModelsToEvaluate(self) -> List[EnergyModelType]:
        include_models = [
            EnergyModelType.SINGLE_SPEED_COMPRESSOR_TRAIN_COMMON_SHAFT,
            EnergyModelType.COMPRESSOR_TRAIN_SIMPLIFIED_WITH_KNOWN_STAGES,
            EnergyModelType.COMPRESSOR_TRAIN_SIMPLIFIED_WITH_UNKNOWN_STAGES,
            EnergyModelType.VARIABLE_SPEED_COMPRESSOR_TRAIN_COMMON_SHAFT,
            EnergyModelType.VARIABLE_SPEED_COMPRESSOR_TRAIN_MULTIPLE_STREAMS_AND_PRESSURES,
        ]
        return include_models

    def evaluate(self, component_model: Any):
        for item in component_model[1].model:
            if not isinstance(item[1], list):
                if item[0] in ItemsToEvaluate.__members__ and item[1] is not None:
                    eval = (
                        Expression.setup_from_expression(item[1])
                        .evaluate(
                            variables=self._variables_map.variables, fill_length=len(self._variables_map.time_vector)
                        )
                        .tolist()
                    )
                    setattr(component_model[1].model, item[0], eval)
            elif item[0] == "stages" and len(item[0]) > 0:
                for stage in item[1]:
                    for variable in stage:
                        if variable[0] in ItemsToEvaluate.__members__ and item[1] is not None:
                            eval = (
                                Expression.setup_from_expression(variable[1])
                                .evaluate(
                                    variables=self._variables_map.variables,
                                    fill_length=len(self._variables_map.time_vector),
                                )
                                .tolist()
                            )
                            setattr(stage, variable[0], eval)
        return component_model

    def get_models(self, energy_usage_model: Dict[datetime, Any], component_type: ComponentType):
        models_to_evaluate = self.ModelsToEvaluate()
        for model_temporal in energy_usage_model.items():
            if component_type in [ComponentType.COMPRESSOR, ComponentType.COMPRESSOR_SYSTEM]:
                if model_temporal[1].model.typ in models_to_evaluate:
                    model_upd = self.evaluate(component_model=model_temporal)
                    energy_usage_model.update({model_temporal[0]: model_upd[1]})
        return energy_usage_model

    def evaluate_dto_for_expressions(self):
        for installation in self._installations:
            for fuel_consumer in installation.fuel_consumers:
                if fuel_consumer.component_type == ComponentType.GENERATOR_SET:
                    for consumer in fuel_consumer.consumers:
                        self.get_models(
                            energy_usage_model=consumer.energy_usage_model, component_type=consumer.component_type
                        )
                        # setattr(component_model[1].model, item[0], eval)
        return self._model
