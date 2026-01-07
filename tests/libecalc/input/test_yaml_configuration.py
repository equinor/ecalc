from datetime import datetime

import pytest
from inline_snapshot import snapshot

from libecalc.presentation.yaml.model import YamlModel
from libecalc.presentation.yaml.model_validation_exception import ModelValidationException
from libecalc.presentation.yaml.yaml_models.pyyaml_yaml_model import PyYamlYamlModel


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
        )

        with pytest.raises(ModelValidationException) as exc_info:
            model.validate_for_run()
        assert str(exc_info.value) == snapshot("""\
Validation error

	Object starting on line 25
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
