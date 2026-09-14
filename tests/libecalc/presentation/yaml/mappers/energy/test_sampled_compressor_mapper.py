import pytest

from libecalc.presentation.yaml.mappers.energy.sampled_compressor_mapper import build_sampled_compressor_model
from libecalc.presentation.yaml.yaml_entities import MemoryResource


class TestBuildSampledCompressorModel:
    def test_fuel_only(self):
        resource = MemoryResource(
            headers=["RATE", "FUEL"],
            data=[[0.0, 100.0, 200.0], [1000.0, 2000.0, 3000.0]],
        )
        model = build_sampled_compressor_model(resource)

        assert model.get_fuel_power_samples() is None
        assert model.evaluate(rate=50.0).energy_usage == pytest.approx(1500.0)

    def test_power_only(self):
        resource = MemoryResource(
            headers=["RATE", "POWER"],
            data=[[0.0, 100.0, 200.0], [1.0, 2.0, 3.0]],
        )
        model = build_sampled_compressor_model(resource)

        assert model.evaluate(rate=50.0).energy_usage == pytest.approx(1.5)

    def test_fuel_and_power_gives_power_interpolation(self):
        resource = MemoryResource(
            headers=["RATE", "FUEL", "POWER"],
            data=[[0.0, 100.0, 200.0], [1000.0, 2000.0, 3000.0], [1.0, 2.0, 3.0]],
        )
        model = build_sampled_compressor_model(resource)

        assert model.get_fuel_power_samples() is not None
        result = model.evaluate(rate=50.0)
        assert result.energy_usage == pytest.approx(1500.0)
        assert result.power == pytest.approx(1.5)

    def test_multiple_variable_columns(self):
        resource = MemoryResource(
            headers=["RATE", "SUCTION_PRESSURE", "DISCHARGE_PRESSURE", "FUEL"],
            data=[
                [0.0, 100.0, 0.0, 100.0, 0.0],
                [10.0, 10.0, 20.0, 20.0, 10.0],
                [50.0, 50.0, 50.0, 50.0, 60.0],
                [1000.0, 2000.0, 1500.0, 2500.0, 1100.0],
            ],
        )
        model = build_sampled_compressor_model(resource)
        assert model.evaluate(rate=1.0, suction_pressure=10.0, discharge_pressure=50.0).energy_usage == pytest.approx(
            1000.0, rel=0.2
        )

    def test_headers_are_case_insensitive(self):
        resource = MemoryResource(
            headers=["rate", "fuel"],
            data=[[0.0, 100.0], [1000.0, 2000.0]],
        )
        model = build_sampled_compressor_model(resource)
        assert model.evaluate(rate=50.0).energy_usage == pytest.approx(1500.0)

    def test_missing_variable_column_raises(self):
        resource = MemoryResource(headers=["FUEL"], data=[[1000.0, 2000.0]])
        with pytest.raises(Exception, match="RATE"):
            build_sampled_compressor_model(resource)

    def test_missing_energy_usage_column_raises(self):
        resource = MemoryResource(headers=["RATE"], data=[[0.0, 100.0]])
        with pytest.raises(Exception, match="FUEL, POWER, or both"):
            build_sampled_compressor_model(resource)
