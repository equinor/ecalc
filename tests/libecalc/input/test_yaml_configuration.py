from datetime import datetime

import pytest
from inline_snapshot import snapshot

from libecalc.presentation.yaml.model import YamlModel
from libecalc.presentation.yaml.model_validation_exception import ModelValidationException
from libecalc.presentation.yaml.yaml_models.pyyaml_yaml_model import PyYamlYamlModel
from libecalc.presentation.yaml.yaml_types.pump.yaml_pump_model import YamlPumpModel
from libecalc.testing.energy_builders import YamlFileBuilder
from libecalc.testing.process_builders import YamlDefinitionsBuilder
from libecalc.testing.pump_builders import (
    YamlPumpBuilder,
    YamlPumpChartBuilder,
    YamlPumpModelBuilder,
    YamlPumpPipelineBuilder,
)
from libecalc.testing.yaml_builder import YamlAssetBuilder


class TestYamlConfiguration:
    @pytest.mark.snapshot
    @pytest.mark.inlinesnapshot
    def test_invalid_timeseries_type(
        self,
        yaml_asset_builder_factory,
        yaml_time_series_factory,
        yaml_asset_configuration_service_factory,
        resource_service_factory,
    ):
        asset = (
            yaml_asset_builder_factory()
            .with_test_data()
            .with_time_series([yaml_time_series_factory().with_test_data().with_type("INVALID").construct()])
            .construct()
        )
        configuration = yaml_asset_configuration_service_factory(asset, name="invalid_model").get_configuration()
        model = YamlModel(
            configuration=configuration,
            resource_service=resource_service_factory({}, configuration=configuration),
            nextgen=True,
        )

        with pytest.raises(ModelValidationException) as exc_info:
            model.validate_for_run()
        assert str(exc_info.value) == snapshot("""\
Validation error

	Object starting on line 6
	Location: TIME_SERIES[0]
	Message: Input tag 'INVALID' found using 'type' | 'TYPE' does not match any of the expected tags: 'DEFAULT', 'MISCELLANEOUS'
""")

    def test_read_dates_from_dict(self):
        yaml_dict = {
            "INSTALLATIONS": {
                "GENERATORSET": {
                    "CONSUMERS": [
                        {datetime(1999, 5, 18): "consumer1"},
                        {datetime(2016, 1, 1): "consumer2"},
                    ]
                },
                "FUELCONSUMERS": [{datetime(2020, 2, 17): "CONSUMER3"}],
            }
        }
        configuration = PyYamlYamlModel(internal_datamodel=yaml_dict, name="test_case", instantiated_through_read=True)
        dates = configuration.dates

        assert len(dates) == 3
        assert dates == {datetime(1999, 5, 18), datetime(2016, 1, 1), datetime(2020, 2, 17)}

    def test_read_chart_curve_files_from_models(self):
        yaml_dict = {
            "MODELS": [
                {
                    "NAME": "singlespeedcompressorchartcsv",
                    "CURVE": {
                        "FILE": "testfile_singlespeed.csv",
                    },
                },
                {
                    "NAME": "variablespeedcompressorchartcsv",
                    "CURVES": {
                        "FILE": "testfile_variablespeed.csv",
                    },
                },
            ],
        }

        configuration = PyYamlYamlModel(internal_datamodel=yaml_dict, name="test_case", instantiated_through_read=True)

        assert [
            resource in configuration.facility_resource_names
            for resource in ["testfile_singlespeed.csv", "testfile_variablespeed.csv"]
        ]

    def test_read_chart_curve_files_from_compressor_models(self):
        yaml_dict = {"DEFINITIONS": {"COMPRESSOR_MODELS": {"model_a": {"CHART": {"CURVES": {"FILE": "chart.csv"}}}}}}

        configuration = PyYamlYamlModel(internal_datamodel=yaml_dict, name="test_case", instantiated_through_read=True)

        assert configuration.facility_resource_names == ["chart.csv"]

    def test_read_pump_chart_files_without_facility_inputs(self, yaml_asset_configuration_service_factory):
        def pump_model_from_file(file: str) -> YamlPumpModel:
            chart = YamlPumpChartBuilder().with_curves(YamlFileBuilder().with_file(file).validate()).validate()
            return YamlPumpModelBuilder().with_chart(chart).validate()

        asset = (
            YamlAssetBuilder()
            .with_test_data()
            .with_definitions(
                YamlDefinitionsBuilder()
                .with_pump_model("pump_model", pump_model_from_file("pump_chart.csv"))
                .validate()
            )
            .with_pumps([YamlPumpBuilder().with_name("pump").validate()])
            .with_pump_pipelines(
                [
                    YamlPumpPipelineBuilder()
                    .with_name("pipeline")
                    .with_pump_item("pump", pump_model_from_file("inline_pump_chart.csv"))
                    .validate()
                ]
            )
            .validate()
        )

        configuration = yaml_asset_configuration_service_factory(asset, name="test_case").get_configuration()

        assert configuration.facility_resource_names == ["pump_chart.csv", "inline_pump_chart.csv"]
