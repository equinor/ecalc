from datetime import datetime

import pytest
from libecalc.presentation.yaml.validation_errors import DataValidationError
from libecalc.presentation.yaml.yaml_keywords import EcalcYamlKeywords
from libecalc.presentation.yaml.yaml_models.pyyaml_yaml_model import PyYamlYamlModel


class TestYamlConfiguration:
    def test_invalid_timeseries_type(self):
        configuration = PyYamlYamlModel(
            internal_datamodel={
                EcalcYamlKeywords.time_series: [
                    {EcalcYamlKeywords.name: "filepath.csv", EcalcYamlKeywords.type: "INVALID"}
                ]
            },
            instantiated_through_read=True,
        )
        with pytest.raises(DataValidationError) as exc_info:
            _ = configuration.timeseries_resources
        assert "Invalid timeseries, type should be one of MISCELLANEOUS, DEFAULT. Got type 'INVALID'." in str(
            exc_info.value
        )

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
        configuration = PyYamlYamlModel(internal_datamodel=yaml_dict, instantiated_through_read=True)
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

        configuration = PyYamlYamlModel(internal_datamodel=yaml_dict, instantiated_through_read=True)

        assert [
            resource in configuration.facility_resource_names
            for resource in ["testfile_singlespeed.csv", "testfile_variablespeed.csv"]
        ]
