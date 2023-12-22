from datetime import datetime
from typing import Any, Dict, List, Union

from libecalc import dto
from libecalc.dto.base import ComponentType
from libecalc.dto.types import EnergyModelType
from libecalc.expression import Expression


class EvaluateModels:
    def __init__(
        self,
        installations: List[dto.components.Installation],
        variables_map: dto.VariablesMap,
    ):
        self._variables_map = variables_map
        self._installations = installations

    def _models_to_evaluate(self) -> List[EnergyModelType]:
        include_models = [
            EnergyModelType.SINGLE_SPEED_COMPRESSOR_TRAIN_COMMON_SHAFT,
            EnergyModelType.COMPRESSOR_TRAIN_SIMPLIFIED_WITH_KNOWN_STAGES,
            EnergyModelType.COMPRESSOR_TRAIN_SIMPLIFIED_WITH_UNKNOWN_STAGES,
            EnergyModelType.VARIABLE_SPEED_COMPRESSOR_TRAIN_COMMON_SHAFT,
            EnergyModelType.VARIABLE_SPEED_COMPRESSOR_TRAIN_MULTIPLE_STREAMS_AND_PRESSURES,
            EnergyModelType.COMPRESSOR_WITH_TURBINE,
        ]
        return include_models

    def _items_to_evaluate(self) -> List[str]:
        include_items = [
            # "calculate_max_rate",
            # "energy_usage_adjustment_constant",
            # "energy_adjustment_factor",
            # "maximum_power",
            "pressure_drop_before_stage"
        ]
        return include_items

    def _evaluate_expression(self, value: Union[float, str, int]) -> List[Union[float, int]]:
        return (
            Expression.setup_from_expression(value)
            .evaluate(variables=self._variables_map.variables, fill_length=len(self._variables_map.time_vector))
            .tolist()
        )

    def _evaluate_and_update(self, component_model: Any):
        items_to_evaluate = self._items_to_evaluate()
        for item in component_model:
            if item[0] == "stage" and item[1] is not None:
                for variable in item[1]:
                    if variable[0] in items_to_evaluate and variable[1] is not None:
                        eval = self._evaluate_expression(variable[1])
                        setattr(item[1], variable[0], eval)
            elif not isinstance(item[1], list):
                if item[0] in items_to_evaluate and item[1] is not None:
                    eval = self._evaluate_expression(item[1])
                    setattr(component_model, item[0], eval)
            elif item[0] == "stages" and len(item[1]) > 0:
                for stage in item[1]:
                    for variable in stage:
                        if variable[0] in items_to_evaluate and variable[1] is not None:
                            eval = self._evaluate_expression(variable[1])
                            setattr(stage, variable[0], eval)

    def _evaluate_model(self, energy_usage_model: Dict[datetime, Any]):
        models_to_evaluate = self._models_to_evaluate()
        for model_temporal in energy_usage_model.items():
            if model_temporal[1].typ == ComponentType.COMPRESSOR_SYSTEM:
                for compressor in model_temporal[1].compressors:
                    if compressor.compressor_train.typ in models_to_evaluate:
                        if compressor.compressor_train.typ == EnergyModelType.COMPRESSOR_WITH_TURBINE:
                            if compressor.compressor_train.compressor_train.typ in models_to_evaluate:
                                self._evaluate_and_update(component_model=compressor.compressor_train.compressor_train)
                        else:
                            self._evaluate_and_update(component_model=compressor.compressor_train)
            else:
                if model_temporal[1].model.typ in models_to_evaluate:
                    if model_temporal[1].model.typ == EnergyModelType.COMPRESSOR_WITH_TURBINE:
                        if model_temporal[1].model.compressor_train.typ in models_to_evaluate:
                            self._evaluate_and_update(component_model=model_temporal[1].model.compressor_train)
                    else:
                        self._evaluate_and_update(component_model=model_temporal[1].model)

    def evaluate_dto_for_expressions(self):
        for installation in self._installations:
            for fuel_consumer in installation.fuel_consumers:
                if fuel_consumer.component_type == ComponentType.GENERATOR_SET:
                    for consumer in fuel_consumer.consumers:
                        if consumer.component_type in [ComponentType.COMPRESSOR, ComponentType.COMPRESSOR_SYSTEM]:
                            self._evaluate_model(energy_usage_model=consumer.energy_usage_model)
                if fuel_consumer.component_type in [ComponentType.COMPRESSOR, ComponentType.COMPRESSOR_SYSTEM]:
                    self._evaluate_model(energy_usage_model=fuel_consumer.energy_usage_model)
        return self._installations
