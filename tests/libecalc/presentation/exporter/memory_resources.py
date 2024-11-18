import pytest

from libecalc.presentation.yaml.yaml_entities import MemoryResource


@pytest.fixture
def generator_electricity2fuel_17MW_resource():
    return MemoryResource(
        data=[
            [0, 0.1, 10, 11, 12, 14, 15, 16, 17, 17.1, 18.5, 20, 20.5, 20.6, 24, 28, 30, 32, 34, 36, 38, 40, 41, 410],
            [
                0,
                75803.4,
                75803.4,
                80759.1,
                85714.8,
                95744,
                100728.8,
                105676.9,
                110598.4,
                136263.4,
                143260,
                151004.1,
                153736.5,
                154084.7,
                171429.6,
                191488,
                201457.5,
                211353.8,
                221196.9,
                231054,
                241049.3,
                251374.6,
                256839.4,
                2568394,
            ],
        ],  # float and int with equal value should count as equal.
        headers=[
            "POWER",
            "FUEL",
        ],
    )


@pytest.fixture
def onshore_power_electricity2fuel_resource():
    return MemoryResource(
        data=[
            [0, 10, 20],
            [0, 0, 0],
        ],  # float and int with equal value should count as equal.
        headers=[
            "POWER",
            "FUEL",
        ],
    )


@pytest.fixture
def cable_loss_time_series_resource():
    return MemoryResource(
        data=[
            [
                "01.01.2021",
                "01.01.2022",
                "01.01.2023",
                "01.01.2024",
                "01.01.2025",
                "01.01.2026",
                "01.01.2027",
                "01.01.2028",
                "01.01.2029",
                "01.01.2030",
            ],
            [0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1],
        ],  # float and int with equal value should count as equal.
        headers=[
            "DATE",
            "CABLE_LOSS_FACTOR",
        ],
    )
