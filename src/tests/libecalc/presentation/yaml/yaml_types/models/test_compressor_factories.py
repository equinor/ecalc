from io import StringIO
from pathlib import Path

import pytest
from models_test_setup import CompressorTrainBase, Models, Stages

from conftest import (
    CurveFactory,
    FluidModelFactory,
    OverridableStreamConfigurationService,
    SingleSpeedChartFactory,
    SingleSpeedTrainFactory,
    StageFactory,
    remove_null_none_empty,
)
from ecalc_cli.infrastructure.file_resource_service import FileResourceService
from libecalc.common.time_utils import Frequency
from libecalc.presentation.yaml.model import YamlModel
from libecalc.presentation.yaml.validation_errors import ValidationError
from libecalc.presentation.yaml.yaml_entities import ResourceStream
from libecalc.presentation.yaml.yaml_keywords import EcalcYamlKeywords
from libecalc.presentation.yaml.yaml_models.pyyaml_yaml_model import PyYamlYamlModel


def test_single_speed_compressor_train() -> None:
    # Build objects for curve, chart, stage, fluid model and compressor
    curve_instance = CurveFactory.build(
        _min_speed=3000,
        _max_speed=6500,
        _min_rate=3500,
        _max_rate=7500,
        _min_head=5000,
        _max_head=9500,
        _min_efficiency=0.7,
        _max_efficiency=0.8,
    )
    chart_instance = SingleSpeedChartFactory.build(name="single_speed_chart", curve=curve_instance)
    stage_instance = StageFactory.build(
        compressor_chart=chart_instance.name, control_margin=0, control_margin_unit="FRACTION"
    )
    fluid_model_instance = FluidModelFactory.build(
        name="fluid_model", fluid_model_type="PREDEFINED", gas_type="DRY", eos_model="SRK"
    )
    compressor_instance = SingleSpeedTrainFactory.build(
        name="single_speed_compressor_train",
        compressor_chart=chart_instance.name,
        compressor_train=Stages(stages=[stage_instance]),
        fluid_model=fluid_model_instance.name,
    )

    # Combine objects into MODELS
    models = Models(
        models=[
            fluid_model_instance,
            chart_instance,
            compressor_instance,
        ]
    )

    # Serialize pydantic model, clean None-data, generate yaml string
    yaml_dict = models.model_dump(by_alias=True)
    cleaned_data = remove_null_none_empty(yaml_dict)
    yaml_string = PyYamlYamlModel.dump_yaml(yaml_dict=cleaned_data)

    # Set up yaml model
    configuration_service = OverridableStreamConfigurationService(
        stream=ResourceStream(name="", stream=StringIO(yaml_string))
    )
    resource_service = FileResourceService(working_directory=Path(""))

    model = YamlModel(
        configuration_service=configuration_service,
        resource_service=resource_service,
        output_frequency=Frequency.YEAR,
    )

    # Validate yaml model
    with pytest.raises(ValidationError) as exc_info:
        model.validate_for_run()

    assert f"{EcalcYamlKeywords.fuel_types}\n" f"\tMessage: This keyword is missing, it is required" in str(
        exc_info.value
    )
    assert isinstance(compressor_instance, CompressorTrainBase)
